# market-data-scraper

A generic REST API poller: exponential backoff with jitter on 429/5xx,
pluggable fetch function, and a choice of CSV or SQLite sink. The example
fetch function hits CoinGecko's public, no-auth `simple/price` endpoint —
swap it for any REST source that returns rows.

## Why the backoff/sink logic is separated from the data source

The part that's actually reusable across projects isn't "how to call
CoinGecko" — it's "how to poll something on an interval without hammering
it during an outage, and where to put the rows once you have them."
`with_backoff` and the two sinks don't know or care what `fetch_fn`
talks to.

## Usage

```python
from poller import fetch_coingecko_simple_price, CsvSink, BackoffConfig, poll_forever

sink = CsvSink("prices.csv", fieldnames=["timestamp", "asset", "price"])
fetch = lambda: fetch_coingecko_simple_price(["bitcoin", "ethereum"])
poll_forever(fetch, sink, interval_seconds=60, backoff=BackoffConfig())
```

Swap `CsvSink` for `SqliteSink(path, table="prices", fieldnames=[...])`
to write to SQLite instead.

## Backoff behavior

On a 429 or 5xx, the delay starts at `base_delay` and doubles each retry
up to `max_delay`, with `jitter` randomizing each sleep so multiple
instances don't retry in lockstep. Gives up after `max_retries` and
raises.

## Tests

All tests mock the HTTP layer — no network calls, no real API rate limits
touched by CI.

```bash
pip install -r requirements.txt pytest
python -m pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
