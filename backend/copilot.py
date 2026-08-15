"""
Phase 5: AI Copilot Layer -- sensitivity analysis, assumption sanity-checks,
and a buy/sell/hold recommendation.

Sensitivity grid is pure math (no AI). The sanity-check and recommendation
agents call Claude, but only to *narrate and critique* numbers already
produced by Phase 1's run_dcf() -- they never compute valuation themselves.
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from schemas import DCFAssumptions, DCFResult
from engine import run_dcf

load_dotenv()


# ---------------------------------------------------------------------------
# 1. Sensitivity analysis -- pure deterministic math, no AI
# ---------------------------------------------------------------------------

class SensitivityCell(BaseModel):
    wacc: float
    terminal_growth_rate: float
    fair_value_per_share: float


class SensitivityGrid(BaseModel):
    cells: List[SensitivityCell]
    wacc_values: List[float]
    terminal_growth_values: List[float]


def run_sensitivity(
    base_assumptions: DCFAssumptions,
    wacc_range: Optional[List[float]] = None,
    terminal_growth_range: Optional[List[float]] = None,
) -> SensitivityGrid:
    """
    Recomputes fair value across a grid of WACC x terminal growth combinations,
    holding every other assumption fixed at base_assumptions' current values.
    Centered on the user's current WACC/terminal growth by default.
    """
    if wacc_range is None:
        w = base_assumptions.wacc
        wacc_range = [w - 0.02, w - 0.01, w, w + 0.01, w + 0.02]

    if terminal_growth_range is None:
        g = base_assumptions.terminal_growth_rate
        terminal_growth_range = [g - 0.01, g - 0.005, g, g + 0.005, g + 0.01]

    cells: List[SensitivityCell] = []
    for wacc in wacc_range:
        for tg in terminal_growth_range:
            if tg >= wacc:
                continue  # invalid combination, skip rather than crash the grid
            trial = base_assumptions.model_copy(update={"wacc": wacc, "terminal_growth_rate": tg})
            result = run_dcf(trial)
            cells.append(SensitivityCell(
                wacc=wacc, terminal_growth_rate=tg,
                fair_value_per_share=result.fair_value_per_share,
            ))

    return SensitivityGrid(cells=cells, wacc_values=wacc_range, terminal_growth_values=terminal_growth_range)


# ---------------------------------------------------------------------------
# 2. Sanity-check agent -- flags outlier assumptions
# ---------------------------------------------------------------------------

class SanityFlag(BaseModel):
    field: str = Field(..., description="Which assumption this flag is about, e.g. 'terminal_growth_rate'")
    severity: str = Field(..., description="'info', 'warning', or 'concern'")
    message: str = Field(..., description="1-2 sentence explanation of the concern, written for a non-expert user")


class SanityCheckResult(BaseModel):
    flags: List[SanityFlag]
    overall_comment: str = Field(..., description="1-2 sentence overall read on how reasonable the assumption set is")


SANITY_SYSTEM_PROMPT = """You are reviewing a DCF's assumptions for red flags, the way a
skeptical senior analyst reviews a junior analyst's model.

Flag anything that looks unreasonable:
- Terminal growth rate above ~3% (above typical long-run GDP growth)
- Revenue growth that stays flat/high for 5 years with no deceleration
- EBIT margins that expand far beyond what's typical for the sector
- WACC that seems too low for the company's apparent risk profile
- CapEx or D&A assumptions wildly different from the company's own history

For each concern, output one SanityFlag. If nothing looks unreasonable, return
an empty flags list and say so in overall_comment. Do not flag things that are
merely aggressive but plausible -- only flag things a careful analyst would
actually push back on.
"""

SANITY_USER_PROMPT = """Ticker: {ticker}

Current assumptions:
Revenue growth by year: {revenue_growth}
EBIT margin by year: {ebit_margin}
Tax rate by year: {tax_rates}
WACC: {wacc:.1%}
Terminal growth rate: {terminal_growth:.1%}

Review these for red flags.
"""


def run_sanity_check(assumptions: DCFAssumptions, model: str = "claude-sonnet-4-6") -> SanityCheckResult:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set in backend/.env")

    llm = ChatAnthropic(model=model, temperature=0)
    structured_llm = llm.with_structured_output(SanityCheckResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SANITY_SYSTEM_PROMPT),
        ("user", SANITY_USER_PROMPT),
    ])

    chain = prompt | structured_llm
    return chain.invoke({
        "ticker": assumptions.ticker,
        "revenue_growth": [f"{g:.1%}" for g in assumptions.revenue_growth_rates],
        "ebit_margin": [f"{m:.1%}" for m in assumptions.ebit_margins],
        "tax_rates": [f"{t:.1%}" for t in assumptions.tax_rates],
        "wacc": assumptions.wacc,
        "terminal_growth": assumptions.terminal_growth_rate,
    })


# ---------------------------------------------------------------------------
# 3. Recommendation agent -- buy/sell/hold framed as "what your inputs imply"
# ---------------------------------------------------------------------------

class Recommendation(BaseModel):
    stance: str = Field(..., description="One of: 'Buy', 'Hold', 'Sell'")
    upside_pct: float = Field(..., description="Fair value / current price - 1, as a decimal")
    explanation: str = Field(
        ..., description="2-4 sentences explaining what's driving the fair value vs market price gap, "
                          "citing the specific assumption(s) most responsible for it"
    )


REC_SYSTEM_PROMPT = """You are explaining what a user's own DCF assumptions imply about
a stock, not giving your own independent opinion. Frame everything as "your inputs imply X,"
never as "I think the stock is worth X." Identify which specific assumption (growth, margin,
WACC, terminal growth) is most responsible for the gap between fair value and market price.

Stance rule: Buy if upside > 15%, Sell if upside < -15%, otherwise Hold.
"""

REC_USER_PROMPT = """Ticker: {ticker}
Current market price: ${current_price:,.2f}
DCF fair value per share: ${fair_value:,.2f}
Implied upside/downside: {upside:.1%}

Assumptions used:
Revenue growth by year: {revenue_growth}
EBIT margin by year: {ebit_margin}
WACC: {wacc:.1%}
Terminal growth rate: {terminal_growth:.1%}

Explain what these inputs imply about the stock.
"""


def get_recommendation(
    assumptions: DCFAssumptions, result: DCFResult, model: str = "claude-sonnet-4-6"
) -> Recommendation:
    if assumptions.current_share_price is None:
        raise ValueError("current_share_price is required on assumptions to generate a recommendation.")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set in backend/.env")

    llm = ChatAnthropic(model=model, temperature=0)
    structured_llm = llm.with_structured_output(Recommendation)

    prompt = ChatPromptTemplate.from_messages([
        ("system", REC_SYSTEM_PROMPT),
        ("user", REC_USER_PROMPT),
    ])

    chain = prompt | structured_llm
    return chain.invoke({
        "ticker": assumptions.ticker,
        "current_price": assumptions.current_share_price,
        "fair_value": result.fair_value_per_share,
        "upside": result.upside_downside or 0.0,
        "revenue_growth": [f"{g:.1%}" for g in assumptions.revenue_growth_rates],
        "ebit_margin": [f"{m:.1%}" for m in assumptions.ebit_margins],
        "wacc": assumptions.wacc,
        "terminal_growth": assumptions.terminal_growth_rate,
    })


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from data_schemas import HistoricalFinancials
    from ratios import compute_ratios
    from seed import seed_assumptions

    hist = HistoricalFinancials(
        ticker="AMZN",
        years=["2017", "2018", "2019", "2020", "2021"],
        revenue=[177866, 232887, 280522, 386064, 469822],
        ebit=[4106, 12421, 14541, 22899, 24879],
        taxes=[770, 1196, 2373, 2863, 4791],
        da=[11478, 15341, 21789, 25251, 34296],
        capex=[11955, 13427, 16861, 40140, 61053],
        nwc_change=[-173, -1043, -2438, 13481, -19611],
        cash=66385, debt=47556, shares_outstanding=10456, current_share_price=122.42,
    )
    ratios = compute_ratios(hist)
    assumptions = seed_assumptions(hist, ratios, wacc=0.0782, terminal_growth_rate=0.03)
    result = run_dcf(assumptions)

    grid = run_sensitivity(assumptions)
    print(f"Sensitivity grid: {len(grid.cells)} combinations computed")

    sanity = run_sanity_check(assumptions)
    print("\nSanity check:", sanity.overall_comment)
    for flag in sanity.flags:
        print(f"  [{flag.severity}] {flag.field}: {flag.message}")

    rec = get_recommendation(assumptions, result)
    print(f"\nRecommendation: {rec.stance} ({rec.upside_pct:.1%})")
    print(rec.explanation)