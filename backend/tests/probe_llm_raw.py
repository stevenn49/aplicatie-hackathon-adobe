"""
Shows the raw OpenRouter response for the executive-summary prompt.

Run from backend/:

    python tests/probe_llm_raw.py

It prints the model's content, any reasoning field, the finish reason and the
token usage, which is what you need when a JSON-mode prompt comes back
unparseable. One live call.
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from services.llm_service import llm_service  # noqa: E402

if not llm_service.enabled:
    print("The LLM is not configured (OPENROUTER_API_KEY / OPENROUTER_MODEL empty).", file=sys.stderr)
    raise SystemExit(1)

payload = {
    "average_sentiment": 76.1,
    "readiness": 65.3,
    "high_priority": 5,
    "recommendations": [
        {"category": "Competitive", "priority": "High", "title": "Close the price & value gap on RTX 5080", "metric": "Price & value 0/100"},
        {"category": "Product", "priority": "High", "title": "Revisit the Galaxy S25 Ultra entry price", "metric": "Price gap +44%"},
    ],
}

prompt = (
    "Market data for a consumer-tech intelligence dashboard:\n"
    f"{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
    "Write a JSON object with exactly two keys: \"headline\" (max 12 words) and "
    "\"body\" (3 sentences, max 90 words). Base every claim on the numbers above. "
    "Do not invent products, prices or trends. Return JSON only."
)

import httpx  # noqa: E402
from config import settings  # noqa: E402

print(f"model: {llm_service.model}")
print(f"max_tokens: {settings.OPENROUTER_MAX_TOKENS}")

response = httpx.post(
    f"{settings.OPENROUTER_BASE_URL}/chat/completions",
    headers={
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_APP_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    },
    json={
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "You are a market strategy analyst. Reply with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": settings.OPENROUTER_MAX_TOKENS,
    },
    timeout=settings.OPENROUTER_TIMEOUT,
)

print(f"\nHTTP {response.status_code}")
data = response.json()
choice = (data.get("choices") or [{}])[0]
message = choice.get("message", {})

print(f"finish_reason: {choice.get('finish_reason')}")
print(f"usage: {json.dumps(data.get('usage', {}), ensure_ascii=False)}")
print(f"\n--- reasoning ---\n{message.get('reasoning') or '(none)'}")
print(f"\n--- content ---\n{message.get('content') or '(empty)'}")

content = (message.get("content") or "").strip()
if content:
    try:
        json.loads(content)
        print("\n[parse] content is valid JSON on its own")
    except Exception as exc:
        print(f"\n[parse] content is NOT valid JSON: {exc}")
