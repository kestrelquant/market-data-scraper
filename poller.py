"""A generic REST API poller: pluggable fetch function, exponential
backoff with jitter on 429/5xx, and a choice of CSV or SQLite sink.

Not tied to one data source on purpose -- `fetch_fn` is any callable that
returns a list of flat dicts. The example in `__main__` hits CoinGecko's
public, no-auth-required simple-price endpoint, but the retry/backoff/sink
plumbing is the reusable part.
"""
from __future__ import annotations

import csv
import logging
import random
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("market-data-scraper")


class RetryableError(Exception):
    pass


@dataclass
class BackoffConfig:
    base_delay: float = 1.0
    max_delay: float = 60.0
    max_retries: int = 5
    jitter: float = 0.3  # fraction of the delay to randomize by


def with_backoff(fn: Callable[[], list[dict]], config: BackoffConfig) -> list[dict]:
    delay = config.base_delay
    last_exc: Exception | None = None

    for attempt in range(1, config.max_retries + 1):
        try:
            return fn()
        except RetryableError as exc:
            last_exc = exc
            sleep_for = min(delay, config.max_delay)
            sleep_for *= 1 + random.uniform(-config.jitter, config.jitter)
            log.warning("attempt %d/%d failed (%s), retrying in %.1fs", attempt, config.max_retries, exc, sleep_for)
            time.sleep(max(0.0, sleep_for))
            delay *= 2

    raise RuntimeError(f"gave up after {config.max_retries} retries") from last_exc


def fetch_coingecko_simple_price(ids: list[str], vs_currency: str = "usd") -> list[dict]:
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(ids), "vs_currencies": vs_currency}

    resp = requests.get(url, params=params, timeout=10)

    if resp.status_code == 429 or resp.status_code >= 500:
        raise RetryableError(f"HTTP {resp.status_code}")
    resp.raise_for_status()

    data = resp.json()
    ts = time.time()
    return [{"timestamp": ts, "asset": asset_id, "price": prices[vs_currency]} for asset_id, prices in data.items()]


class CsvSink:
    def __init__(self, path: str | Path, fieldnames: list[str]):
        self.path = Path(path)
        self.fieldnames = fieldnames
        is_new = not self.path.exists()
        self._file = open(self.path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=fieldnames)
        if is_new:
            self._writer.writeheader()

    def write(self, rows: Iterable[dict]) -> None:
        for row in rows:
            self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()


class SqliteSink:
    def __init__(self, path: str | Path, table: str, fieldnames: list[str]):
        self.table = table
        self._conn = sqlite3.connect(path)
        cols = ", ".join(f'"{f}" REAL' if f != "asset" else f'"{f}" TEXT' for f in fieldnames)
        self._conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols})')
        self._conn.commit()
        self._fieldnames = fieldnames

    def write(self, rows: Iterable[dict]) -> None:
        placeholders = ", ".join("?" for _ in self._fieldnames)
        cols = ", ".join(f'"{f}"' for f in self._fieldnames)
        for row in rows:
            values = [row[f] for f in self._fieldnames]
            self._conn.execute(f'INSERT INTO "{self.table}" ({cols}) VALUES ({placeholders})', values)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def poll_forever(fetch_fn: Callable[[], list[dict]], sink, interval_seconds: float, backoff: BackoffConfig) -> None:
    while True:
        rows = with_backoff(fetch_fn, backoff)
        sink.write(rows)
        log.info("wrote %d row(s)", len(rows))
        time.sleep(interval_seconds)


if __name__ == "__main__":
    sink = CsvSink("prices.csv", fieldnames=["timestamp", "asset", "price"])
    fetch = lambda: fetch_coingecko_simple_price(["bitcoin", "ethereum"])
    try:
        poll_forever(fetch, sink, interval_seconds=60, backoff=BackoffConfig())
    finally:
        sink.close()
