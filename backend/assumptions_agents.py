"""
Phase 3: AI agent that proposes DCF forward assumptions.

Takes historical financials/ratios (Phase 2) and calls Claude via LangChain
to propose growth, margin, WACC, and terminal growth assumptions -- with a
written rationale per assumption -- instead of the naive flat-average
seeding from Phase 2's seed_assumptions().

The LLM NEVER does DCF math. It only outputs assumption numbers + reasoning.
Those numbers get fed into Phase 1's run_dcf(), which is the only place
actual valuation arithmetic happens.
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

from schemas import DCFAssumptions
from data_schemas import HistoricalFinancials, HistoricalRatios

load_dotenv()


# ---------------------------------------------------------------------------
# Structured output schema -- the LLM is forced to fill exactly this shape.
# Includes a rationale per bucket so the dashboard can show "why" next to
# each suggested slider position.
# ---------------------------------------------------------------------------

class AssumptionProposal(BaseModel):
    """The LLM's proposed forward assumptions for one company, with reasoning."""

    revenue_growth_rates: List[float] = Field(
        ..., description="Proposed yearly revenue growth rates as decimals, one per projection year, e.g. [0.10, 0.09, 0.08, 0.07, 0.06]"
    )
    revenue_growth_rationale: str = Field(
        ..., description="1-2 sentence explanation grounded in historical trends and typical growth deceleration"
    )

    ebit_margins: List[float] = Field(..., description="Proposed EBIT margin per projection year, as decimals")
    ebit_margin_rationale: str = Field(..., description="1-2 sentence explanation")

    tax_rates: List[float] = Field(..., description="Proposed effective tax rate per projection year, as decimals")
    tax_rate_rationale: str = Field(..., description="1-2 sentence explanation")

    da_pct_sales: List[float] = Field(..., description="Proposed D&A as % of revenue per projection year, as decimals")
    capex_pct_sales: List[float] = Field(..., description="Proposed CapEx as % of revenue per projection year, as decimals")
    nwc_change_pct_sales: List[float] = Field(..., description="Proposed change in NWC as % of revenue per projection year, as decimals")
    capital_intensity_rationale: str = Field(
        ..., description="1-2 sentence explanation covering D&A, CapEx, and NWC trends together"
    )

    wacc: float = Field(..., description="Proposed WACC as a decimal, e.g. 0.09 for 9%")
    wacc_rationale: str = Field(..., description="1-2 sentence explanation, e.g. referencing sector risk/capital structure")

    terminal_growth_rate: float = Field(
        ..., description="Proposed terminal growth rate as a decimal, must be modest (roughly GDP-level, 2-3%) and strictly below WACC"
    )
    terminal_growth_rationale: str = Field(..., description="1-2 sentence explanation")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an equity research analyst proposing DCF forward assumptions.

You will be given a company's historical financials and derived ratios. Propose
forward-looking assumptions for the next {projection_years} years.

Rules you must follow:
- Do NOT simply repeat the most recent year's numbers flat across all years.
  Growth rates should generally decelerate over the projection period toward
  a mature, sustainable rate, unless the historical trend clearly justifies otherwise.
- Terminal growth rate must be modest (roughly GDP-level, ~2-3%) and strictly
  below your proposed WACC.
- Be skeptical of outlier historical years (e.g. one-off spikes or crashes) --
  don't let a single unusual year dominate your forward assumptions.
- Ground every number in the historical data you were given; do not invent
  figures unrelated to the company's actual trend.
- Output ONLY the structured fields requested. No extra commentary outside
  the rationale fields.
"""

USER_PROMPT = """Company: {ticker}

Historical years: {years}

Revenue growth by year: {revenue_growth}
EBIT margin by year: {ebit_margin}
Tax rate by year: {tax_rate}
D&A % of sales by year: {da_pct_sales}
CapEx % of sales by year: {capex_pct_sales}
Change in NWC % of sales by year: {nwc_change_pct_sales}

Most recent year revenue: {base_revenue:,.0f}

Propose assumptions for the next {projection_years} years.
"""


def _build_prompt(hist: HistoricalFinancials, ratios: HistoricalRatios, projection_years: int) -> ChatPromptTemplate:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", USER_PROMPT),
    ])
    return prompt.partial(
        projection_years=projection_years,
        ticker=hist.ticker,
        years=", ".join(hist.years),
        revenue_growth=[f"{g:.1%}" for g in ratios.revenue_growth],
        ebit_margin=[f"{m:.1%}" for m in ratios.ebit_margin],
        tax_rate=[f"{t:.1%}" for t in ratios.tax_rate],
        da_pct_sales=[f"{d:.1%}" for d in ratios.da_pct_sales],
        capex_pct_sales=[f"{c:.1%}" for c in ratios.capex_pct_sales],
        nwc_change_pct_sales=[f"{n:.1%}" for n in ratios.nwc_change_pct_sales],
        base_revenue=hist.revenue[-1],
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def propose_assumptions(
    hist: HistoricalFinancials,
    ratios: HistoricalRatios,
    projection_years: int = 5,
    model: str = "claude-sonnet-4-6",
) -> tuple[DCFAssumptions, AssumptionProposal]:
    """
    Calls Claude to propose DCF assumptions for a company, then converts the
    result into a DCFAssumptions object ready to pass straight into run_dcf().

    Returns both:
      - the DCFAssumptions object (for the engine / sliders)
      - the raw AssumptionProposal (for displaying rationale in the UI)
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy backend/.env.example to backend/.env "
            "and add your key before calling propose_assumptions()."
        )

    llm = ChatAnthropic(model=model, temperature=0)
    structured_llm = llm.with_structured_output(AssumptionProposal)

    prompt = _build_prompt(hist, ratios, projection_years)
    chain = prompt | structured_llm

    proposal: AssumptionProposal = chain.invoke({})

    year_labels = [str(int(hist.years[-1]) + i + 1) for i in range(projection_years)]

    assumptions = DCFAssumptions(
        ticker=hist.ticker,
        base_revenue=hist.revenue[-1],
        revenue_growth_rates=proposal.revenue_growth_rates,
        ebit_margins=proposal.ebit_margins,
        tax_rates=proposal.tax_rates,
        da_pct_sales=proposal.da_pct_sales,
        capex_pct_sales=proposal.capex_pct_sales,
        nwc_change_pct_sales=proposal.nwc_change_pct_sales,
        wacc=proposal.wacc,
        terminal_growth_rate=proposal.terminal_growth_rate,
        cash=hist.cash,
        debt=hist.debt,
        shares_outstanding=hist.shares_outstanding,
        current_share_price=hist.current_share_price,
        year_labels=year_labels,
    )

    return assumptions, proposal


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from data_schemas import fetch_financials, compute_ratios
    from schemas import run_dcf, print_dcf_report

    hist = fetch_financials("AMZN")
    ratios = compute_ratios(hist)

    assumptions, proposal = propose_assumptions(hist, ratios, projection_years=5)

    print("--- AI Rationale ---")
    print("Growth:", proposal.revenue_growth_rationale)
    print("Margins:", proposal.ebit_margin_rationale)
    print("Tax:", proposal.tax_rate_rationale)
    print("Capital intensity:", proposal.capital_intensity_rationale)
    print("WACC:", proposal.wacc_rationale)
    print("Terminal growth:", proposal.terminal_growth_rationale)

    result = run_dcf(assumptions)
    print_dcf_report(assumptions, result)