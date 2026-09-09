"""One example data source. Any callable returning list[dict] works with
`poll_forever` -- this module isn't special, it's just the one shipped
as a working reference.
"""
from __future__ import annotations

import time

import requests

from ..backoff import RetryableError


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
