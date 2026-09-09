from __future__ import annotations

import logging
import time
from typing import Callable

from .backoff import BackoffConfig, with_backoff

log = logging.getLogger("market-data-scraper")


def poll_forever(fetch_fn: Callable[[], list[dict]], sink, interval_seconds: float, backoff: BackoffConfig) -> None:
    while True:
        rows = with_backoff(fetch_fn, backoff)
        sink.write(rows)
        log.info("wrote %d row(s)", len(rows))
        time.sleep(interval_seconds)
