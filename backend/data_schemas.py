from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class DCFAssumptions(BaseModel):
    ticker: str
    base_revenue: float = Field(..., gt=0)

    revenue_growth_rates: List[float]
    ebit_margins: List[float]
    tax_rates: List[float]
    da_pct_sales: List[float]
    capex_pct_sales: List[float]
    nwc_change_pct_sales: List[float]

    wacc: float = Field(..., gt=0, lt=1)
    terminal_growth_rate: float

    cash: float = 0.0
    debt: float = 0.0
    shares_outstanding: float = Field(..., gt=0)

    current_share_price: Optional[float] = Field(None, gt=0)
    year_labels: Optional[List[str]] = None

    @field_validator("ebit_margins", "tax_rates", "da_pct_sales", "capex_pct_sales", "nwc_change_pct_sales")
    @classmethod
    def matching_length(cls, v, info):
        growth = info.data.get("revenue_growth_rates")
        if growth is not None and len(v) != len(growth):
            raise ValueError(f"'{info.field_name}' has {len(v)} years but revenue_growth_rates has {len(growth)}. All per-year assumption lists must be the same length.")
        return v

    @field_validator("year_labels")
    @classmethod
    def labels_match_length(cls, v, info):
        if v is None:
            return v
        growth = info.data.get("revenue_growth_rates")
        if growth is not None and len(v) != len(growth):
            raise ValueError(f"year_labels has {len(v)} entries but revenue_growth_rates has {len(growth)}.")
        return v

    @field_validator("terminal_growth_rate")
    @classmethod
    def terminal_below_wacc(cls, v, info):
        wacc = info.data.get("wacc")
        if wacc is not None and v >= wacc:
            raise ValueError(f"terminal_growth_rate ({v}) must be less than wacc ({wacc}).")
        return v

    @property
    def projection_years(self) -> int:
        return len(self.revenue_growth_rates)


class YearLine(BaseModel):
    year_label: str
    revenue: float
    revenue_growth: float
    ebit: float
    ebit_margin: float
    taxes: float
    tax_pct_ebit: float
    ebiat: float
    da: float
    da_pct_sales: float
    capex: float
    capex_pct_sales: float
    nwc_change: float
    nwc_pct_sales: float
    unlevered_fcf: float
    discount_factor: float
    pv_fcf: float


class DCFResult(BaseModel):
    lines: List[YearLine]
    terminal_value: float
    pv_terminal_value: float
    enterprise_value: float
    equity_value: float
    fair_value_per_share: float
    sum_pv_fcf: float
    upside_downside: Optional[float] = None