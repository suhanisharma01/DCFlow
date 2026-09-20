# DCFlow

An interactive DCF valuation dashboard where AI handles the repetitive work — pulling financials, suggesting starting assumptions, sanity-checking inputs — while the user makes the actual judgment calls via sliders that recalculate the model instantly.

Live app: https://dc-flow.vercel.app/dashboard


## Core design decision

**The AI never does arithmetic.** Every valuation number (projected FCF, terminal value, fair value/share) comes from one deterministic Python function, `run_dcf()` in `engine.py` — no LLM involved. It's been validated line-for-line against a real banker-built DCF template, reproducing a $140.02 AMZN fair value exactly.

AI is used only for four things, all downstream of that engine:
1. Proposing starting assumptions from historical financials, with rationale
2. Flagging outlier/unreasonable assumptions
3. Explaining what the user's current inputs imply about the stock (buy/hold/sell)
4. Answering free-form questions about the current valuation via an embedded chatbot — which reads existing results but never calculates anything itself

## Features

- **Live ticker data** — pulls real financials via yfinance for 7 supported companies, cached locally to avoid rate-limiting
- **AI-suggested assumptions** — LLM proposes growth, margin, WACC, and terminal growth with written rationale, grounded in historical trends
- **Real-time sliders** — 15+ adjustable assumptions recalculate fair value instantly via FastAPI, no AI in the hot path
- **Bull/Base/Bear scenarios** — automatically computed alongside the base case for quick sensitivity comparison
- **AI investment read** — compares fair value to market price and explains the gap in terms of the user's own inputs
- **In-app chatbot** — ask questions about the current valuation ("why is fair value low?"), grounded in already-computed results
- **Excel export** — downloads a fully formula-driven `.xlsx`, editable natively in Excel

## How it works

1. `fetcher.py` pulls real financials (yfinance, disk-cached) → `ratios.py` derives historical growth/margins
2. `assumptions_agents.py` (AI) proposes forward assumptions to seed the sliders
3. User adjusts sliders → `POST /dcf/calculate` → `run_dcf()` recalculates instantly, no AI
4. `POST /dcf/recommendation` — AI explains fair value vs. market price
5. `POST /dcf/chat` — conversational Q&A grounded in current assumptions/results, no computation
6. `POST /dcf/export-excel` — downloads a formula-driven `.xlsx`, fully editable

## Setup

```bash
cd DCFlow/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# create .env in backend/ with:
# OPENAI_API_KEY=sk-your-key-here

uvicorn api:app --reload --port 8000
```

```bash
cd ../frontend
npm install && npm run dev
```

## Deployment

- **Backend**: Render (FastAPI, root dir `backend`, start command `uvicorn api:app --host 0.0.0.0 --port $PORT`)
- **Frontend**: Vercel (Next.js, root dir `frontend`, env var `NEXT_PUBLIC_API_BASE` pointing to the Render URL)

## Stack

Python, FastAPI, Pydantic · LangChain + OpenAI (structured output only) · yfinance · React/Next.js, Tailwind, Recharts · openpyxl

## Endpoints

| Endpoint | AI? | Purpose |
|---|---|---|
| `/dcf/calculate` | No | Core valuation |
| `/dcf/load-ticker` | Yes | Fetch financials + AI-proposed assumptions |
| `/dcf/recommendation` | Yes | Buy/hold/sell |
| `/dcf/chat` | Yes | Conversational Q&A on current valuation |
| `/dcf/export-excel` | No | Formula-driven Excel export |

## A known limitation, worth understanding

The naive fallback default (averaging recent historical years, held flat) can produce misleading results when a historical year is an outlier — e.g., using Amazon's actual 2020 COVID-inflated growth rate flat across 5 years crushes free cash flow because CapEx scales with an unrealistic growth assumption. This is exactly the kind of blind spot the AI sanity-check and chatbot are built to catch, and why the dashboard treats AI-suggested numbers as a *starting point*, not a final answer.
