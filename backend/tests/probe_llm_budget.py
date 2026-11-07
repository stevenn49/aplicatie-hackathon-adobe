"""
Finds the token budget a reasoning model needs for the JSON summary prompt.

Run from backend/:

    python tests/probe_llm_budget.py [model ...]

With no arguments it uses OPENROUTER_MODEL from backend/.env. For each model it
tries the executive-summary prompt at increasing max_tokens and reports the
first budget that produces parseable JSON, plus how many tokens went to
reasoning. Live calls: one per budget per model.
"""
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("OPENROUTER_MODEL", "").strip()

if not API_KEY:
    print("OPENROUTER_API_KEY is not set in backend/.env", file=sys.stderr)
    raise SystemExit(1)

MODELS = sys.argv[1:] or ([DEFAULT_MODEL] if DEFAULT_MODEL else [])
if not MODELS:
    print("No model: pass one as an argument or set OPENROUTER_MODEL.", file=sys.stderr)
    raise SystemExit(1)

PAYLOAD = {
    "average_sentiment": 76.1,
    "readiness": 65.3,
    "high_priority": 5,
    "recommendations": [
        {"category": "Competitive", "priority": "High", "title": "Close the price & value gap on RTX 5080", "metric": "Price & value 0/100"},
        {"category": "Product", "priority": "High", "title": "Revisit the Galaxy S25 Ultra entry price", "metric": "Price gap +44%"},
    ],
}

PROMPT = (
    "Market data for a consumer-tech intelligence dashboard:\n"
    f"{json.dumps(PAYLOAD, ensure_ascii=False, indent=2)}\n\n"
    "Write a JSON object with exactly two keys: \"headline\" (max 12 words) and "
    "\"body\" (3 sentences, max 90 words). Base every claim on the numbers above. "
    "Do not invent products, prices or trends. Return JSON only."
)

BUDGETS = [900, 2000, 4000, 8000]


def extract_json(text):
    """The model may wrap the object in prose or a code fence."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except Exception:
        return None


def try_budget(model, budget):
    response = httpx.post(
        f"{BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("OPENROUTER_APP_URL", "http://localhost:5173"),
            "X-Title": os.environ.get("OPENROUTER_APP_NAME", "MarketPulse AI"),
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a market strategy analyst. Reply with JSON only."},
                {"role": "user", "content": PROMPT},
            ],
            "temperature": 0.2,
            "max_tokens": budget,
        },
        timeout=180,
    )
    if response.status_code != 200:
        return {"ok": False, "error": f"HTTP {response.status_code}: {response.text[:160]}"}

    data = response.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {})
    content = (message.get("content") or "").strip()
    usage = data.get("usage") or {}
    reasoning_tokens = (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")

    parsed = extract_json(content) if content else None
    return {
        "ok": parsed is not None,
        "finish": choice.get("finish_reason"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": reasoning_tokens,
        "content": content[:200],
        "parsed": parsed,
    }


for model in MODELS:
    print(f"\n=== {model} ===")
    for budget in BUDGETS:
        result = try_budget(model, budget)
        if result.get("error"):
            print(f"  max_tokens={budget:<5} {result['error']}")
            break
        status = "JSON OK" if result["ok"] else f"no JSON (finish={result['finish']})"
        print(
            f"  max_tokens={budget:<5} {status:<28} "
            f"completion={result['completion_tokens']} reasoning={result['reasoning_tokens']}"
        )
        if result["ok"]:
            print(f"    headline: {result['parsed'].get('headline')}")
            break
