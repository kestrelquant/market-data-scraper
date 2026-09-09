import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from market_data_scraper import BackoffConfig, CsvSink, RetryableError, SqliteSink, with_backoff
from market_data_scraper.sources.coingecko import fetch_coingecko_simple_price


def test_with_backoff_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableError("boom")
        return [{"ok": True}]

    result = with_backoff(flaky, BackoffConfig(base_delay=0.01, max_retries=5))
    assert result == [{"ok": True}]
    assert calls["n"] == 3


def test_with_backoff_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)

    def always_fails():
        raise RetryableError("nope")

    with pytest.raises(RuntimeError):
        with_backoff(always_fails, BackoffConfig(base_delay=0.01, max_retries=3))


def test_fetch_coingecko_raises_retryable_on_429():
    fake_resp = MagicMock(status_code=429)
    with patch("market_data_scraper.sources.coingecko.requests.get", return_value=fake_resp):
        with pytest.raises(RetryableError):
            fetch_coingecko_simple_price(["bitcoin"])


def test_fetch_coingecko_parses_response():
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {"bitcoin": {"usd": 65000.0}}
    fake_resp.raise_for_status.return_value = None
    with patch("market_data_scraper.sources.coingecko.requests.get", return_value=fake_resp):
        rows = fetch_coingecko_simple_price(["bitcoin"])
    assert rows[0]["asset"] == "bitcoin"
    assert rows[0]["price"] == 65000.0
    assert "timestamp" in rows[0]


def test_csv_sink_writes_header_once_and_appends(tmp_path):
    path = tmp_path / "out.csv"
    sink = CsvSink(path, fieldnames=["timestamp", "asset", "price"])
    sink.write([{"timestamp": 1, "asset": "bitcoin", "price": 100}])
    sink.close()

    sink2 = CsvSink(path, fieldnames=["timestamp", "asset", "price"])
    sink2.write([{"timestamp": 2, "asset": "bitcoin", "price": 200}])
    sink2.close()

    lines = path.read_text().strip().splitlines()
    assert lines[0] == "timestamp,asset,price"
    assert len(lines) == 3  # header + 2 data rows


def test_sqlite_sink_creates_table_and_inserts(tmp_path):
    path = tmp_path / "out.db"
    sink = SqliteSink(path, table="prices", fieldnames=["timestamp", "asset", "price"])
    sink.write([{"timestamp": 1.0, "asset": "bitcoin", "price": 100.0}])

    cur = sink._conn.execute("SELECT asset, price FROM prices")
    row = cur.fetchone()
    sink.close()

    assert row == ("bitcoin", 100.0)
