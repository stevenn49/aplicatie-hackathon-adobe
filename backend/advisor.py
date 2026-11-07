"""MarketPulse AI marketing advisor, powered by free AI models.

Supported providers (all speak the OpenAI-compatible chat API):
  openrouter  free models, one key for all of them       https://openrouter.ai/keys (default)
  groq        free tier, very fast, needs a free key     https://console.groq.com/keys
  gemini      Google AI Studio free tier, free key       https://aistudio.google.com/apikey
  ollama      runs models on your own PC, no key, offline https://ollama.com/download

Pick one with AI_PROVIDER in backend/.env (or --provider on the CLI).
Core logic shared by the CLI (marketing_advisor.py) and the API (server.py).
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("marketpulse.advisor")

DEFAULT_OPENROUTER_MODEL = "stealth/crouton-alpha"

# Default models are tried in order; free models change often, so override them with
# AI_MODELS=a,b,c in .env and run `python marketing_advisor.py --list-models` to see options.
PROVIDERS = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "signup": "https://openrouter.ai/keys",
        # OPENROUTER_MODEL overrides this list; the fallbacks are free models.
        "models": [DEFAULT_OPENROUTER_MODEL],
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "signup": "https://console.groq.com/keys",
        "models": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant"],
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "signup": "https://aistudio.google.com/apikey",
        "models": ["gemini-flash-latest", "gemini-flash-lite-latest"],
    },
    "ollama": {
        "url": os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1",
        "key_env": None,
        "signup": "https://ollama.com/download",
        "models": [],  # empty = use the first model you have pulled locally
    },
}

DEFAULT_PROVIDER = "openrouter"

PROVIDER = ""
API_KEY = ""
MODELS: list[str] = []
TIMEOUT = int(os.getenv("AI_TIMEOUT", "120"))


def set_provider(name: str | None = None) -> None:
    """Select the provider (defaults to AI_PROVIDER from .env, else openrouter)."""
    global PROVIDER, API_KEY, MODELS
    name = (name or os.getenv("AI_PROVIDER") or DEFAULT_PROVIDER).lower()
    if name not in PROVIDERS:
        raise AdvisorError(f"Unknown provider '{name}'. Choose one of: {', '.join(PROVIDERS)}")
    PROVIDER = name
    cfg = PROVIDERS[name]
    API_KEY = os.getenv(cfg["key_env"], "") if cfg["key_env"] else "ollama"

    override = os.getenv("AI_MODELS", "")
    models = [m.strip() for m in override.split(",") if m.strip()]
    if not models and name == "openrouter":
        # The same model the main API uses, so one setting drives both surfaces.
        configured = os.getenv("OPENROUTER_MODEL", "").strip()
        if configured:
            models = [configured]
    MODELS = models or list(cfg["models"])


CATEGORIES = ["Product", "Consumer", "Marketing", "Competitive"]
PRIORITIES = ["High", "Medium", "Low"]
ROUTES = {"Product": "/products", "Consumer": "/consumers", "Marketing": "/marketing", "Competitive": "/competitors"}
ICONS = {"Product": "target", "Consumer": "users", "Marketing": "sparkles", "Competitive": "swords"}


class AdvisorError(RuntimeError):
    pass


set_provider()


MARKET_DATA_CACHE_TTL = 120
_market_data_cache: dict = {"at": 0.0, "data": None, "source": ""}


def _api_base() -> str:
    """The main API, which owns the live MySQL data."""
    return os.getenv("MARKETPULSE_API_URL", "http://127.0.0.1:8010").rstrip("/")


def _fetch_json(path: str, timeout: int = 10):
    response = requests.get(f"{_api_base()}{path}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def _live_market_data() -> dict | None:
    """
    Builds the context the assistant needs from the running API, so every number
    it quotes comes from MySQL rather than from a snapshot file.

    Returns None when the API is unreachable; the caller then falls back to
    market_data.json and says so.
    """
    try:
        overview = _fetch_json("/api/analytics/overview")
        brands = _fetch_json("/api/analytics/brands")
        products = _fetch_json("/api/products")
        segments = _fetch_json("/api/analytics/consumer-segments")
        sentiment = _fetch_json("/api/analytics/sentiment")
        competitors = _fetch_json("/api/analytics/competitors")
    except Exception as exc:
        logger.warning(f"Live market data unavailable ({exc}); falling back to market_data.json")
        return None

    return {
        "source": "live",
        "kpis": overview.get("kpis", []),
        "brands": [
            {"name": b.get("name"), "color": b.get("color"), "share": b.get("share"), "health": b.get("health")}
            for b in competitors.get("brands", [])
        ],
        "brandStats": [
            {
                "brand": b.get("brand"),
                "shareOfVoice": b.get("shareOfVoice"),
                "mentions": b.get("mentions"),
                "sentiment": b.get("sentiment"),
                "health": b.get("health"),
                "topics": b.get("topics", []),
                "concerns": b.get("concerns", []),
            }
            for b in brands
        ],
        "products": [
            {
                "name": p.get("name"),
                "brand": p.get("brand"),
                "category": p.get("category"),
                "price": p.get("price"),
                "currency": p.get("currency"),
                "rating": p.get("rating"),
                "sentiment": p.get("sentiment"),
                "change": p.get("change"),
                "interest": p.get("interest"),
                "review_count": p.get("review_count"),
                "pros": p.get("pros", []),
                "cons": p.get("cons", []),
            }
            for p in products
        ],
        "segments": segments,
        "sentiment": {
            "distribution": sentiment.get("distribution", []),
            "aspects": sentiment.get("aspects", []),
            "keywords": sentiment.get("keywords", []),
            "reviews": sentiment.get("reviews", []),
            "total_reviews": sentiment.get("total_reviews", 0),
        },
        "mentions": overview.get("mentions", []),
        "competitors": competitors,
    }


def load_market_data(force: bool = False) -> dict:
    """
    The data the assistant reasons about.

    Prefers the live API (MySQL) and caches it for two minutes. Falls back to the
    bundled market_data.json only when the API is unreachable, and marks the
    result `source: "snapshot"` so the prompt can tell the model which it is.
    """
    now = time.time()
    cached = _market_data_cache
    if not force and cached["data"] is not None and now - cached["at"] < MARKET_DATA_CACHE_TTL:
        return cached["data"]

    live = _live_market_data()
    if live is not None:
        cached.update({"at": now, "data": live, "source": "live"})
        return live

    with open(BASE_DIR / "market_data.json", encoding="utf-8") as f:
        snapshot = json.load(f)
    snapshot["source"] = "snapshot"
    cached.update({"at": now, "data": snapshot, "source": "snapshot"})
    return snapshot


def build_context(data: dict, brand: str | None = None) -> str:
    """Compact text summary of the dashboard data for the prompt."""
    keep = lambda item: not brand or item.get("brand") == brand or item.get("name") == brand
    ctx = {
        "kpis": data["kpis"],
        "brands": [b for b in data["brands"] if keep(b)],
        "brandStats": [b for b in data["brandStats"] if keep(b)],
        "products": [
            {k: p[k] for k in ("name", "brand", "category", "price", "rating", "sentiment", "change", "interest", "pros", "cons")}
            for p in data["products"] if keep(p)
        ],
        "consumerSegments": data["segments"],
        "sentimentAspects": data["sentiment"]["aspects"],
        "keywords": data["sentiment"]["keywords"],
        "recentReviews": [
            {k: r[k] for k in ("brand", "product", "text", "rating", "sentiment", "source")}
            for r in data["sentiment"]["reviews"] if keep(r)
        ],
        "socialMentions": [
            {k: m[k] for k in ("brand", "text", "source", "sentiment", "engagement")}
            for m in data["mentions"] if keep(m)
        ],
    }
    return json.dumps(ctx, ensure_ascii=False)


SYSTEM_PROMPT = (
    "You are MarketPulse AI, a senior marketing strategist for consumer tech brands. "
    "Base every recommendation on the market data you are given: cite concrete numbers "
    "(sentiment scores, price, share of voice, segment size, interest change). "
    "Be specific and actionable. Never invent metrics that are not in the data."
)


def chat(messages: list[dict], json_mode: bool = False, temperature: float = 0.6) -> tuple[str, str]:
    """Send a chat request, falling back through MODELS. Returns (text, model_used)."""
    cfg = PROVIDERS[PROVIDER]
    if not API_KEY:
        raise AdvisorError(
            f"{cfg['key_env']} is not set. Create a free key at {cfg['signup']} "
            "and put it in backend/.env (see backend/.env.example)."
        )
    models = MODELS or [m["id"] for m in list_models()][:1]
    if not models:
        raise AdvisorError("No Ollama models installed. Run e.g. `ollama pull llama3.2` first.")
    url = f"{cfg['url']}/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    if PROVIDER == "openrouter":
        # OpenRouter attributes traffic by these headers; they are optional but
        # they make the app visible in the account's activity page.
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_APP_URL", "http://localhost:5173")
        headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "MarketPulse AI")
    errors = []
    for model in models:
        body = {"model": model, "messages": messages, "temperature": temperature}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
            # Some free models reject response_format; retry once without it.
            if resp.status_code == 400 and json_mode:
                body.pop("response_format")
                resp = requests.post(url, headers=headers, json=body, timeout=TIMEOUT)
        except requests.ConnectionError as exc:
            if PROVIDER == "ollama":
                raise AdvisorError("Cannot reach Ollama at localhost:11434. Install it from https://ollama.com and make sure it is running.") from exc
            errors.append(f"{model}: {exc}")
            continue
        except requests.RequestException as exc:
            errors.append(f"{model}: {exc}")
            continue
        if resp.status_code == 401:
            raise AdvisorError(f"{PROVIDER} rejected the API key (401). Check {cfg['key_env']}.")
        if not resp.ok:
            errors.append(f"{model}: HTTP {resp.status_code} {resp.text[:200]}")
            continue
        payload = resp.json()
        if isinstance(payload, list):  # Gemini sometimes wraps errors in a list
            payload = payload[0] if payload else {}
        if "error" in payload:
            errors.append(f"{model}: {payload['error'].get('message', payload['error'])}")
            continue
        try:
            text = payload["choices"][0]["message"]["content"] or ""
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)  # reasoning models
        except (KeyError, IndexError):
            errors.append(f"{model}: unexpected response {str(payload)[:200]}")
            continue
        if text.strip():
            return text.strip(), payload.get("model", model)
        errors.append(f"{model}: empty response")
    raise AdvisorError("All models failed:\n  " + "\n  ".join(errors))


OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))  # Ollama's 4k default is too small for the market data


def _pick_models() -> list[str]:
    models = MODELS or [m["id"] for m in list_models()][:1]
    if not models:
        raise AdvisorError("No Ollama models installed. Run e.g. `ollama pull llama3.2` first.")
    return models


def stream_chat(messages: list[dict], temperature: float = 0.6):
    """Yield (chunk, model) pairs as the model generates text.

    Errors are raised before the first chunk (so callers can return a clean HTTP error);
    models are tried in order until one starts producing text.
    """
    cfg = PROVIDERS[PROVIDER]
    if not API_KEY:
        raise AdvisorError(f"{cfg['key_env']} is not set. Create a free key at {cfg['signup']} and put it in backend/.env.")
    errors = []
    for model in _pick_models():
        try:
            if PROVIDER == "ollama":
                # Native API: lets us raise the context window (the /v1 endpoint cannot).
                base = os.getenv("OLLAMA_URL", "http://localhost:11434")
                resp = requests.post(f"{base}/api/chat", stream=True, timeout=TIMEOUT, json={
                    "model": model, "messages": messages, "stream": True,
                    "options": {"temperature": temperature, "num_ctx": OLLAMA_NUM_CTX},
                })
            else:
                headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
                if PROVIDER == "openrouter":
                    headers["HTTP-Referer"] = os.getenv("OPENROUTER_APP_URL", "http://localhost:5173")
                    headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "MarketPulse AI")
                resp = requests.post(f"{cfg['url']}/chat/completions", headers=headers, stream=True, timeout=TIMEOUT,
                                     json={"model": model, "messages": messages, "temperature": temperature, "stream": True})
        except requests.ConnectionError as exc:
            if PROVIDER == "ollama":
                raise AdvisorError("Cannot reach Ollama at localhost:11434. Start the Ollama app (or `ollama serve`).") from exc
            errors.append(f"{model}: {exc}")
            continue
        if resp.status_code == 401:
            raise AdvisorError(f"{PROVIDER} rejected the API key (401). Check {cfg['key_env']}.")
        if not resp.ok:
            errors.append(f"{model}: HTTP {resp.status_code} {resp.text[:200]}")
            continue
        resp.encoding = "utf-8"
        started = False
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if PROVIDER == "ollama":
                event = json.loads(line)
                if "error" in event:
                    raise AdvisorError(event["error"])
                text = event.get("message", {}).get("content", "")
                done = event.get("done")
            else:
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                event = json.loads(data)
                if "error" in event:
                    if started:
                        raise AdvisorError(str(event["error"]))
                    errors.append(f"{model}: {event['error']}")
                    break
                text = ((event.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                done = False
            if text:
                started = True
                yield text, model
            if done:
                break
        if started:
            return
        errors.append(f"{model}: empty response")
    raise AdvisorError("All models failed:\n  " + "\n  ".join(errors))


def get_advice(question: str, brand: str | None = None, history: list[dict] | None = None) -> tuple[str, str]:
    """Free-form marketing advice in Markdown. Returns (answer, model_used)."""
    data = load_market_data()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nMARKET DATA (JSON):\n" + build_context(data, brand)},
        *(history or []),
        {"role": "user", "content": question},
    ]
    return chat(messages)


def _extract_json(text: str):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        if not match:
            raise AdvisorError(f"Model did not return JSON: {text[:300]}")
        return json.loads(match.group(1))


def _normalize(items: list, data: dict) -> list[dict]:
    product_brand = {p["name"]: p["brand"] for p in data["products"]}
    brands = {b["name"] for b in data["brands"]}
    out = []
    for i, item in enumerate(items, 1):
        if not isinstance(item, dict) or not item.get("title"):
            continue
        category = item.get("category") if item.get("category") in CATEGORIES else "Marketing"
        priority = str(item.get("priority", "Medium")).capitalize()
        priority = priority if priority in PRIORITIES else "Medium"
        try:
            confidence = max(0, min(100, int(float(item.get("confidence", 75)))))
        except (TypeError, ValueError):
            confidence = 75
        related = str(item.get("related", "")).strip()
        # The dashboard filters by "related.startsWith(brand)", so keep "Brand · Product" format.
        if " · " not in related and related not in brands:
            low = related.lower()
            match = next((n for n in product_brand if low and (low in n.lower() or n.lower() in low)), None)
            if match:
                related = f"{product_brand[match]} · {match}"
            elif related not in brands:
                b = next((b for b in brands if low.startswith(b.lower())), None)
                related = f"{b} · {related[len(b):].strip()}" if b else (related or "Market")
        out.append({
            "id": f"ai{i}",
            "category": category,
            "priority": priority,
            "title": str(item["title"]).strip(),
            "detail": str(item.get("detail", "")).strip(),
            "metric": str(item.get("metric", "")).strip(),
            "confidence": confidence,
            "related": related,
            "route": ROUTES[category],
            "icon": ICONS[category],
        })
    order = {p: n for n, p in enumerate(PRIORITIES)}
    return sorted(out, key=lambda r: (order[r["priority"]], -r["confidence"]))


def get_recommendations(brand: str | None = None, category: str | None = None, count: int = 5) -> tuple[list[dict], str]:
    """Structured recommendations in the same shape the dashboard's InsightCard uses."""
    data = load_market_data()
    example = data["exampleRecommendations"][0]
    example = {k: example[k] for k in ("category", "priority", "title", "detail", "metric", "confidence", "related")}
    focus = []
    if brand:
        focus.append(f"Focus only on {brand}.")
    if category and category in CATEGORIES:
        focus.append(f"Every recommendation must have category \"{category}\".")
    prompt = (
        f"Generate {count} marketing recommendations from the market data. {' '.join(focus)}\n"
        "Respond with ONLY a JSON object of the form {\"recommendations\": [...]}. Each item has:\n"
        f"- category: one of {CATEGORIES}\n"
        f"- priority: one of {PRIORITIES}\n"
        "- title: short imperative headline (max 8 words)\n"
        "- detail: 1-2 sentences of evidence and the action to take\n"
        "- metric: the key supporting number, e.g. \"Price sensitivity +18%\"\n"
        "- confidence: integer 0-100\n"
        "- related: \"Brand · Product\" exactly as named in the data\n"
        f"Example item: {json.dumps(example, ensure_ascii=False)}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\nMARKET DATA (JSON):\n" + build_context(data, brand)},
        {"role": "user", "content": prompt},
    ]
    text, model = chat(messages, json_mode=True, temperature=0.4)
    parsed = _extract_json(text)
    items = parsed.get("recommendations", []) if isinstance(parsed, dict) else parsed
    recs = _normalize(items, data)
    if not recs:
        raise AdvisorError(f"Model returned no usable recommendations: {text[:300]}")
    return recs, model


def list_models() -> list[dict]:
    """Models available from the current provider."""
    cfg = PROVIDERS[PROVIDER]
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    if PROVIDER == "gemini":
        headers = {"x-goog-api-key": API_KEY}
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
    else:
        url = f"{cfg['url']}/models"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.ConnectionError as exc:
        raise AdvisorError(f"Cannot reach {PROVIDER} at {url}") from exc
    if not resp.ok:
        raise AdvisorError(f"Listing models failed: HTTP {resp.status_code} {resp.text[:200]}")
    data = resp.json()
    if PROVIDER == "gemini":
        return sorted(({"id": m["name"].removeprefix("models/"), "context": m.get("inputTokenLimit"), "name": m.get("displayName", "")}
                       for m in data.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])),
                      key=lambda m: m["id"])
    out = []
    for m in data.get("data", []):
        out.append({"id": m["id"], "context": m.get("context_length") or m.get("context_window"),
                    "name": m.get("name") or m.get("owned_by", "")})
    return sorted(out, key=lambda m: m["id"])
