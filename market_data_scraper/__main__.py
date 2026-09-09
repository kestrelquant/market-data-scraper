"""python -m market_data_scraper -- polls CoinGecko for BTC/ETH prices
into prices.csv every 60s. Swap the fetch function and sink for anything
else that fits the same shapes.
"""
from . import BackoffConfig, CsvSink, fetch_coingecko_simple_price, poll_forever


def main() -> None:
    sink = CsvSink("prices.csv", fieldnames=["timestamp", "asset", "price"])
    fetch = lambda: fetch_coingecko_simple_price(["bitcoin", "ethereum"])
    try:
        poll_forever(fetch, sink, interval_seconds=60, backoff=BackoffConfig())
    finally:
        sink.close()


if __name__ == "__main__":
    main()
