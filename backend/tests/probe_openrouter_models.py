"""
One-off probe: which free OpenRouter models actually answer from this machine?

Run from backend/:

    python tests/probe_openrouter_models.py

It reads OPENROUTER_API_KEY from backend/.env, asks the public catalogue for the
free models, then sends a one-token prompt to each and prints the outcome. A
model can be listed as free and still be rejected with 403 for a region, which
is exactly what this finds.

Live external calls: one per model. Do not run it in a loop.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not API_KEY:
    print("OPENROUTER_API_KEY is not set in backend/.env", file=sys.stderr)
    raise SystemExit(1)


def free_models():
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        catalogue = json.load(response)["data"]

    def is_zero(value):
        try:
            return float(value) == 0.0
        except (TypeError, ValueError):
            return False

    models = []
    for model in catalogue:
        pricing = model.get("pricing") or {}
        if is_zero(pricing.get("prompt")) and is_zero(pricing.get("completion")):
            models.append({
                "id": model["id"],
                "context": int(model.get("context_length") or 0),
            })
    models.sort(key=lambda item: (-item["context"], item["id"]))
    return models


def probe(model_id):
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
        "max_tokens": 8,
        "temperature": 0,
    }).encode()
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5173",
            "X-Title": "MarketPulse AI",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.load(response)
        choices = payload.get("choices") or []
        text = (choices[0].get("message", {}).get("content") or "") if choices else ""
        return ("OK", text.strip()[:40]) if text.strip() else ("EMPTY", str(payload)[:80])
    except urllib.error.HTTPError as exc:
        try:
            message = json.load(exc).get("error", {}).get("message", "")
        except Exception:
            message = ""
        return (f"HTTP {exc.code}", message[:110])
    except Exception as exc:  # network, timeout
        return ("ERROR", str(exc)[:80])


def main():
    models = free_models()
    print(f"{len(models)} free models in the catalogue; probing each one.\n")
    working = []
    for model in models:
        status, detail = probe(model["id"])
        context = f"{model['context'] // 1000}k" if model["context"] else "?"
        print(f"  {status:<10} {context:>6}  {model['id']}")
        if status == "OK":
            working.append(model["id"])
        elif detail:
            print(f"             {detail}")

    print("\nModels that answered:")
    for model_id in working:
        print(f"  {model_id}")
    if not working:
        print("  (none)")


if __name__ == "__main__":
    main()
