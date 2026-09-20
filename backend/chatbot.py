"""
Chatbot: answers questions about the current DCF valuation.
Has read access to the current assumptions/result -- never computes
anything itself. Can suggest assumption changes; the frontend decides
whether to apply them via the sliders.
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

from schemas import DCFAssumptions, DCFResult

load_dotenv()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    assumptions: DCFAssumptions
    result: Optional[DCFResult] = None


class SuggestedChange(BaseModel):
    field: str = Field(..., description="Which assumption field to change, e.g. 'wacc'")
    year_index: Optional[int] = Field(None, description="If per-year field, which year (0-indexed)")
    new_value: float


class ChatResponse(BaseModel):
    reply: str
    suggested_changes: List[SuggestedChange] = []


CHAT_SYSTEM_PROMPT = """You are a helpful assistant embedded in a DCF valuation dashboard.
You can see the user's current assumptions and computed valuation results below.

Rules:
- Never do arithmetic yourself. All numbers you reference must come from the
  data provided to you, not calculations you perform.
- If the user asks "what if" questions (e.g. "what if WACC were 10%?"), you may
  suggest specific assumption changes in suggested_changes, but do NOT state
  what the new fair value would be -- you don't know, since you don't run the
  actual DCF engine. Just say something like "try that and see how it moves the numbers."
- Keep answers conversational, 2-4 sentences, unless the user asks for detail.
- If asked about something outside this DCF's scope (unrelated stocks, general
  advice, etc.), answer briefly and redirect to what you can help with here.

Current assumptions:
Ticker: {ticker}
Revenue growth by year: {revenue_growth}
EBIT margin by year: {ebit_margin}
WACC: {wacc:.1%}
Terminal growth rate: {terminal_growth:.1%}

Current results:
Fair value per share: ${fair_value}
Current market price: ${current_price}
Upside/downside: {upside}
"""


def chat(request: ChatRequest, model: str = "gpt-4o-mini") -> ChatResponse:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in backend/.env")

    a = request.assumptions
    r = request.result

    system_content = CHAT_SYSTEM_PROMPT.format(
        ticker=a.ticker,
        revenue_growth=[f"{g:.1%}" for g in a.revenue_growth_rates],
        ebit_margin=[f"{m:.1%}" for m in a.ebit_margins],
        wacc=a.wacc,
        terminal_growth=a.terminal_growth_rate,
        fair_value=f"{r.fair_value_per_share:.2f}" if r else "not yet calculated",
        current_price=a.current_share_price or "unknown",
        upside=f"{r.upside_downside:.1%}" if r and r.upside_downside is not None else "unknown",
    )

    llm = ChatOpenAI(model=model, temperature=0.3)
    structured_llm = llm.with_structured_output(ChatResponse)

    lc_messages = [SystemMessage(content=system_content)]
    for m in request.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        else:
            lc_messages.append(AIMessage(content=m.content))

    response = structured_llm.invoke(lc_messages)
    return response