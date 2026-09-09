# market-data-scraper

A generic REST API poller with exponential backoff, pluggable data
sources, and a choice of CSV or SQLite output.

## Problem

Polling a rate-limited API on an interval sounds trivial until an outage
hits: no backoff means hammering a struggling endpoint with the exact
same request every few seconds, and no jitter means a fleet of pollers
all retrying in lockstep. Most one-off scraper scripts skip this
entirely because it's not the interesting part of the task — until the
data source has a bad day and the script either floods it or silently
stops producing rows.

## Solution

The backoff and storage logic (`backoff.py`, `sinks/`) know nothing
about any specific API — they operate on a plain `fetch_fn() -> list[dict]`
callable. The shipped source (`sources/coingecko.py`) hits CoinGecko's
public, no-auth `simple/price` endpoint as a working reference; pointing
this at a different API is a new file under `sources/`, not a rewrite.

## Architecture

```
market_data_scraper/
  backoff.py           BackoffConfig, RetryableError, with_backoff -- no source/sink knowledge
  poller.py             poll_forever(fetch_fn, sink, interval, backoff)
  sources/
    coingecko.py         fetch_coingecko_simple_price -- one example source
  sinks/
    csv_sink.py           CsvSink
    sqlite_sink.py         SqliteSink
  __main__.py            python -m market_data_scraper
```

## Installation

```bash
git clone https://github.com/kestrelquant/market-data-scraper
cd market-data-scraper
pip install -r requirements.txt
```

## Usage

```bash
python -m market_data_scraper
```

or as a library:

```python
from market_data_scraper import fetch_coingecko_simple_price, CsvSink, BackoffConfig, poll_forever

sink = CsvSink("prices.csv", fieldnames=["timestamp", "asset", "price"])
fetch = lambda: fetch_coingecko_simple_price(["bitcoin", "ethereum"])
poll_forever(fetch, sink, interval_seconds=60, backoff=BackoffConfig())
```

Swap `CsvSink` for `SqliteSink(path, table="prices", fieldnames=[...])`
to write to SQLite instead.

## Backoff behavior

On a 429 or 5xx, the delay starts at `base_delay` and doubles each retry
up to `max_delay`, with `jitter` randomizing each sleep so multiple
instances don't retry in lockstep. Gives up and raises after
`max_retries`.

## Tests

All tests mock the HTTP layer — no network calls, no real API rate
limits touched by CI.

```bash
pip install -r requirements.txt pytest
python -m pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).
