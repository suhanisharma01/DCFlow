from pydantic import BaseModel, Field
from typing import List, Optional


class HistoricalFinancials(BaseModel):
    """Cleaned historical financials for one ticker, most recent year last."""

    ticker: str
    years: List[str] = Field(..., description="Fiscal year labels, oldest to most recent")

    revenue: List[float]
    ebit: List[float]
    taxes: List[float]
    da: List[float]
    capex: List[float]
    nwc_change: List[float]

    cash: float
    debt: float
    shares_outstanding: float
    current_share_price: Optional[float] = None

    @property
    def num_years(self) -> int:
        return len(self.years)


class HistoricalRatios(BaseModel):
    """Derived per-year ratios."""

    years: List[str]
    revenue_growth: List[float]
    ebit_margin: List[float]
    tax_rate: List[float]
    da_pct_sales: List[float]
    capex_pct_sales: List[float]
    nwc_change_pct_sales: List[float]