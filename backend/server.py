"""FastAPI server exposing the marketing advisor to the dashboard.

Run:  uvicorn server:app --reload --port 8000   (from the backend/ folder)
"""
from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import advisor
import assistant

app = FastAPI(title="MarketPulse AI Advisor")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Intent", "X-Model"],
)

# Free models are rate-limited, so cache generated recommendations for a while.
CACHE_TTL = 600
_cache: dict[tuple, tuple[float, list, str]] = {}


class AdviceRequest(BaseModel):
    question: str
    brand: str | None = None
    history: list[dict] = []


@app.get("/health")
def health():
    return {"ok": True, "provider": advisor.PROVIDER, "models": advisor.MODELS, "key_configured": bool(advisor.API_KEY)}


@app.get("/analytics/recommendations")
def recommendations(category: str | None = None, brand: str | None = None, refresh: bool = False):
    category = category if category in advisor.CATEGORIES else None
    brand = None if brand in (None, "", "All brands") else brand
    key = (category, brand)
    cached = _cache.get(key)
    if cached and not refresh and time.time() - cached[0] < CACHE_TTL:
        return cached[1]
    try:
        recs, model = advisor.get_recommendations(brand, category)
    except advisor.AdvisorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    _cache[key] = (time.time(), recs, model)
    return recs


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    brand: str | None = None
    page: dict | None = None          # {"path", "title", "filters"}
    charts: list[dict] = []           # [{"id", "title", "subtitle", "data": [...], "note"}]
    focusChart: str | None = None     # id of the chart the user clicked "Analyse" on


@app.post("/ai/chat")
def ai_chat(req: ChatRequest):
    """Streams the assistant's Markdown answer as plain text."""
    try:
        intent, model, chunks = assistant.stream_answer(
            req.message, req.history[-12:], req.brand, req.page, req.charts, req.focusChart)
    except advisor.AdvisorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    def body():
        try:
            yield from chunks
        except Exception as exc:  # stream already started; report inline
            yield f"\n\n_[Generation interrupted: {exc}]_"

    return StreamingResponse(body(), media_type="text/plain; charset=utf-8",
                             headers={"X-Intent": intent, "X-Model": model, "Cache-Control": "no-cache"})


@app.post("/ai/advice")
def advice(req: AdviceRequest):
    try:
        answer, model = advisor.get_advice(req.question, req.brand, req.history[-10:])
    except advisor.AdvisorError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"answer": answer, "model": model}
