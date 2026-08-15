from .schemas import HistoricalFinancials, HistoricalRatios


def compute_ratios(hist: HistoricalFinancials) -> HistoricalRatios:
    revenue = hist.revenue
    n = len(revenue)

    if n < 2:
        raise ValueError("Need at least 2 years of history to compute growth rates.")

    revenue_growth = [
        (revenue[i] / revenue[i - 1]) - 1 if revenue[i - 1] else 0.0
        for i in range(1, n)
    ]

    def safe_ratio(numerator_list):
        return [
            (numerator_list[i] / revenue[i]) if revenue[i] else 0.0
            for i in range(n)
        ]

    ebit_margin = safe_ratio(hist.ebit)
    tax_rate = [
        (hist.taxes[i] / hist.ebit[i]) if hist.ebit[i] else 0.0
        for i in range(n)
    ]
    da_pct_sales = safe_ratio(hist.da)
    capex_pct_sales = safe_ratio(hist.capex)
    nwc_change_pct_sales = safe_ratio(hist.nwc_change)

    return HistoricalRatios(
        years=hist.years,
        revenue_growth=revenue_growth,
        ebit_margin=ebit_margin,
        tax_rate=tax_rate,
        da_pct_sales=da_pct_sales,
        capex_pct_sales=capex_pct_sales,
        nwc_change_pct_sales=nwc_change_pct_sales,
    )