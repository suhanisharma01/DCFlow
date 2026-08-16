# DCFlow

An interactive DCF valuation dashboard where AI handles the repetitive work — pulling financials, suggesting starting assumptions, sanity-checking inputs — while the user makes the actual judgment calls via sliders that recalculate the model instantly.

## Core design decision

**The AI never does arithmetic.** Every valuation number (projected FCF, terminal value, fair value/share) comes from one deterministic Python function, `run_dcf()` in `engine.py` — no LLM involved. It's been validated line-for-line against a real banker-built DCF (reproduces a $140.02 AMZN fair value exactly against a known template).

AI is used only for three things, all downstream of that engine:
1. Proposing starting assumptions from historical financials, with rationale
2. Flagging outlier/unreasonable assumptions
3. Explaining what the user's current inputs imply about the stock (buy/hold/sell)

## How it works

1. `fetcher.py` pulls real financials (yfinance) → `ratios.py` derives historical growth/margins
2. `assumptions_agents.py` (AI) proposes forward assumptions to seed the sliders
3. User adjusts sliders → `POST /dcf/calculate` → `run_dcf()` recalculates instantly, no AI
4. `POST /dcf/sensitivity` — WACC × terminal growth grid, pure math
5. `POST /dcf/recommendation` — AI explains fair value vs. market price
6. `POST /dcf/export-excel` — downloads a formula-driven `.xlsx`, fully editable

## Setup

```bash
cd DCFlow/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

uvicorn api:app --reload --port 8000
```

```bash
cd ../frontend
npm install && npm run dev
```

## Stack

Python, FastAPI, Pydantic · LangChain + Claude (structured output only) · yfinance · React/Next.js · openpyxl

## Endpoints

| Endpoint | AI? | Purpose |
|---|---|---|
| `/dcf/calculate` | No | Core valuation |
| `/dcf/sensitivity` | No | WACC × terminal growth grid |
| `/dcf/sanity-check` | Yes | Flags outlier assumptions |
| `/dcf/recommendation` | Yes | Buy/hold/sell |
| `/dcf/export-excel` | No | Formula-driven Excel export |
