"""
Pulls historical financials for a ticker, preferring a local disk cache
(built once via build_cache.py) over a live yfinance call. Live fetching
depends on curl_cffi impersonation to get past Yahoo's bot detection, which
is fragile -- reading from disk avoids that path entirely for any ticker
that's already been cached.
"""

import json
import os

from schemas import HistoricalFinancials

CACHE_FILE = os.path.join(os.path.dirname(__file__), "ticker_cache.json")


def _load_disk_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


_disk_cache = _load_disk_cache()
_memory_cache = {}


def fetch_financials(ticker: str, years_back: int = 3) -> HistoricalFinancials:
    ticker = ticker.upper()

    if ticker in _memory_cache:
        return _memory_cache[ticker]

    if ticker in _disk_cache:
        result = HistoricalFinancials(**_disk_cache[ticker])
        _memory_cache[ticker] = result
        return result

    # Only reached for tickers not in ticker_cache.json -- falls back to a
    # live fetch. This is the fragile path (Yahoo bot detection / curl_cffi).
    return _fetch_live(ticker, years_back)


def _fetch_live(ticker: str, years_back: int = 3) -> HistoricalFinancials:
    import yfinance as yf
    #from curl_cffi import requests as curl_requests

    ROW_ALIASES = {
        "revenue": ["Total Revenue", "Operating Revenue"],
        "ebit": ["Operating Income", "EBIT"],
        "taxes": ["Tax Provision", "Income Tax Expense"],
        "da": ["Depreciation And Amortization", "Depreciation Amortization Depletion"],
        "capex": ["Capital Expenditure", "Purchase Of PPE"],
        "nwc_change": ["Change In Working Capital"],
        "cash": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
        "debt": ["Total Debt", "Long Term Debt"],
        "shares": ["Ordinary Shares Number", "Share Issued"],
    }

    def _get_row(df, keys):
        for key in keys:
            if key in df.index:
                return list(df.loc[key][::-1].values)
        return None

    #session = curl_requests.Session(impersonate="chrome")
    #stock = yf.Ticker(ticker, session=session)
    stock = yf.Ticker(ticker)

    income = stock.financials
    cashflow = stock.cashflow
    balance = stock.balance_sheet

    if income is None or income.empty:
        raise ValueError(f"No income statement data returned for ticker '{ticker}'.")

    year_columns = list(income.columns[::-1])[-years_back:]
    years = [col.strftime("%Y") for col in year_columns]

    def slice_recent(values):
        return values[-years_back:] if values else [0.0] * years_back

    revenue = slice_recent(_get_row(income, ROW_ALIASES["revenue"]))
    ebit = slice_recent(_get_row(income, ROW_ALIASES["ebit"]))
    taxes = slice_recent(_get_row(income, ROW_ALIASES["taxes"]))

    da = slice_recent(_get_row(cashflow, ROW_ALIASES["da"]))
    capex_raw = slice_recent(_get_row(cashflow, ROW_ALIASES["capex"]))
    capex = [abs(x) for x in capex_raw]

    nwc_change_raw = _get_row(cashflow, ROW_ALIASES["nwc_change"])
    nwc_change = [0.0] * years_back if nwc_change_raw is None else [-x for x in slice_recent(nwc_change_raw)]

    if revenue is None or ebit is None:
        raise ValueError(f"Could not find revenue or EBIT for '{ticker}' under any known row alias.")

    cash_row = _get_row(balance, ROW_ALIASES["cash"])
    debt_row = _get_row(balance, ROW_ALIASES["debt"])
    shares_row = _get_row(balance, ROW_ALIASES["shares"])

    cash = cash_row[-1] if cash_row else 0.0
    debt = debt_row[-1] if debt_row else 0.0
    shares_outstanding = shares_row[-1] if shares_row else 0.0

    current_price = None
    try:
        current_price = stock.fast_info.get("lastPrice")
    except Exception:
        pass

    result = HistoricalFinancials(
        ticker=ticker,
        years=years,
        revenue=revenue,
        ebit=ebit,
        taxes=taxes,
        da=da,
        capex=capex,
        nwc_change=nwc_change,
        cash=cash,
        debt=debt,
        shares_outstanding=shares_outstanding,
        current_share_price=current_price,
    )

    _memory_cache[ticker] = result
    return result