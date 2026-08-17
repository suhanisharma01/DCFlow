"""
One-time script: fetches each supported ticker's financials and saves them
to a local JSON cache. Run this once (retrying individual tickers if
rate-limited), then the app reads from disk instead of hitting Yahoo live.
"""

import json
import time
from fetcher import fetch_financials

SUPPORTED_TICKERS = ["AMZN", "AAPL", "MSFT", "GOOGL", "META", "NFLX", "TSLA"]
CACHE_FILE = "ticker_cache.json"

def build_cache():
    cache = {}
    for ticker in SUPPORTED_TICKERS:
        print(f"Fetching {ticker}...")
        try:
            hist = fetch_financials(ticker)
            cache[ticker] = hist.model_dump()
            print(f"  OK")
        except Exception as e:
            print(f"  FAILED: {e}")
        time.sleep(5)  # slow down between calls to avoid triggering rate limits

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    print(f"\nSaved {len(cache)}/{len(SUPPORTED_TICKERS)} tickers to {CACHE_FILE}")

if __name__ == "__main__":
    build_cache()