from schemas import DCFAssumptions
from .schemas import HistoricalFinancials, HistoricalRatios


def _avg_recent(values, lookback=2):
    recent = values[-lookback:] if len(values) >= lookback else values
    return sum(recent) / len(recent)


def seed_assumptions(
    hist: HistoricalFinancials,
    ratios: HistoricalRatios,
    projection_years: int = 5,
    terminal_growth_rate: float = 0.025,
    wacc: float = 0.09,
) -> DCFAssumptions:
    avg_growth = _avg_recent(ratios.revenue_growth)
    avg_ebit_margin = _avg_recent(ratios.ebit_margin)
    avg_tax_rate = _avg_recent(ratios.tax_rate)
    avg_da_pct = _avg_recent(ratios.da_pct_sales)
    avg_capex_pct = _avg_recent(ratios.capex_pct_sales)
    avg_nwc_pct = _avg_recent(ratios.nwc_change_pct_sales)

    if wacc <= terminal_growth_rate:
        wacc = terminal_growth_rate + 0.02

    year_labels = [str(int(hist.years[-1]) + i + 1) for i in range(projection_years)]

    return DCFAssumptions(
        ticker=hist.ticker,
        base_revenue=hist.revenue[-1],
        revenue_growth_rates=[avg_growth] * projection_years,
        ebit_margins=[avg_ebit_margin] * projection_years,
        tax_rates=[avg_tax_rate] * projection_years,
        da_pct_sales=[avg_da_pct] * projection_years,
        capex_pct_sales=[avg_capex_pct] * projection_years,
        nwc_change_pct_sales=[avg_nwc_pct] * projection_years,
        wacc=wacc,
        terminal_growth_rate=terminal_growth_rate,
        cash=hist.cash,
        debt=hist.debt,
        shares_outstanding=hist.shares_outstanding,
        current_share_price=hist.current_share_price,
        year_labels=year_labels,
    )