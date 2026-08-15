import yfinance as yf
from .schemas import HistoricalFinancials


ROW_ALIASES = {
    "revenue": ["Total Revenue", "Operating Revenue"],
    "ebit": ["Operating Income", "EBIT"],
    "taxes": ["Tax Provision", "Income Tax Expense"],
    "da": ["Depreciation And Amortization", "Depreciation Amortization Depletion"],
    "capex": ["Capital Expenditure", "Purchase Of PPE"],
    "nwc_change": ["Change In Working Capital"],
    "cash": ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"],
    "debt": ["Total Debt", "Long Term Debt"],
}


def _get_row(df, keys, default=0.0):
    for key in keys:
        if key in df.index:
            return list(df.loc[key][::-1].values)
    return None


def fetch_financials(ticker: str, years_back: int = 3) -> HistoricalFinancials:
    stock = yf.Ticker(ticker)

    income = stock.financials
    cashflow = stock.cashflow
    balance = stock.balance_sheet
    info = stock.info

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
    if nwc_change_raw is None:
        nwc_change = [0.0] * years_back
    else:
        nwc_change = slice_recent(nwc_change_raw)
        nwc_change = [-x for x in nwc_change]

    if revenue is None or ebit is None:
        raise ValueError(
            f"Could not find revenue or EBIT for '{ticker}' under any known row alias."
        )

    cash_row = _get_row(balance, ROW_ALIASES["cash"])
    debt_row = _get_row(balance, ROW_ALIASES["debt"])
    cash = cash_row[-1] if cash_row else 0.0
    debt = debt_row[-1] if debt_row else 0.0

    shares_outstanding = info.get("sharesOutstanding", 0.0)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")

    return HistoricalFinancials(
        ticker=ticker.upper(),
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