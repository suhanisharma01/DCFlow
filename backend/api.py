"""
Phase 4: FastAPI backend exposing the DCF engine for real-time slider recalculation.

Run with: uvicorn api:app --reload --port 8000
"""

import os
import tempfile

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import ValidationError

from data_schemas import DCFAssumptions, DCFResult
from engine import run_dcf
from copilot import run_sensitivity, run_sanity_check, get_recommendation, SensitivityGrid, SanityCheckResult, Recommendation
from excel_export import export_dcf_to_excel

app = FastAPI(title="DCFlow DCF API")

# Allow the frontend dev server to call this API directly.
# Tighten allow_origins to your actual deployed frontend URL before shipping.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/dcf/calculate", response_model=DCFResult)
def calculate_dcf(assumptions: DCFAssumptions) -> DCFResult:
    """
    Takes a full set of DCF assumptions (whatever the sliders currently show)
    and returns the recalculated valuation. Called on every slider release.
    """
    try:
        return run_dcf(assumptions)
    except ZeroDivisionError:
        raise HTTPException(
            status_code=400,
            detail="terminal_growth_rate is too close to wacc, causing a divide-by-zero in terminal value.",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/dcf/sensitivity", response_model=SensitivityGrid)
def sensitivity(assumptions: DCFAssumptions) -> SensitivityGrid:
    """Pure math -- WACC x terminal growth grid centered on current assumptions."""
    try:
        return run_sensitivity(assumptions)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/dcf/sanity-check", response_model=SanityCheckResult)
def sanity_check(assumptions: DCFAssumptions) -> SanityCheckResult:
    """AI -- flags outlier assumptions. Debounce on the frontend; don't call on every keystroke."""
    try:
        return run_sanity_check(assumptions)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/dcf/recommendation", response_model=Recommendation)
def recommendation(assumptions: DCFAssumptions) -> Recommendation:
    """AI -- buy/sell/hold framed as 'what your inputs imply', not the model's own opinion."""
    try:
        result = run_dcf(assumptions)
        return get_recommendation(assumptions, result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/dcf/export-excel")
def export_excel(assumptions: DCFAssumptions):
    """
    Generates a formula-driven .xlsx for the given assumptions and returns it
    as a downloadable file. Uses a temp file per request rather than a fixed
    path so concurrent exports for different tickers don't collide.
    """
    try:
        with tempfile.NamedTemporaryFile(
            suffix=f"_{assumptions.ticker}_dcf.xlsx", delete=False
        ) as tmp:
            filepath = tmp.name

        export_dcf_to_excel(assumptions, filepath)

        return FileResponse(
            path=filepath,
            filename=f"{assumptions.ticker}_dcf.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/health")
def health_check():
    return {"status": "ok"}