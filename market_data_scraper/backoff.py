"""Exponential backoff with jitter -- the part of a poller that's reusable
across any data source, which is why it doesn't import any of them.
"""
from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Callable

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
