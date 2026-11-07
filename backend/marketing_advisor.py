"""Command-line marketing chatbot using free AI models (local Ollama, or Groq / Gemini).

Examples:
  python marketing_advisor.py "How should Samsung respond to charging-speed complaints?"
  python marketing_advisor.py --brand Sony "Plan a launch campaign for the WH-1000XM6"
  python marketing_advisor.py --recommendations --brand NVIDIA
  python marketing_advisor.py --chat
  python marketing_advisor.py --list-models
  python marketing_advisor.py --provider ollama --chat      # fully local, no API key
"""
from __future__ import annotations

import argparse
import json
import sys

import advisor


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles + "·" / "″" characters

    parser = argparse.ArgumentParser(description="MarketPulse AI marketing advisor (free AI models)")
    parser.add_argument("question", nargs="*", help="Marketing question to ask")
    parser.add_argument("--brand", help="Limit the market data to one brand (Apple, NVIDIA, Microsoft, Samsung, Sony)")
    parser.add_argument("--recommendations", action="store_true", help="Generate structured dashboard recommendations (JSON)")
    parser.add_argument("--category", choices=advisor.CATEGORIES, help="Category for --recommendations")
    parser.add_argument("--count", type=int, default=5, help="Number of recommendations (default 5)")
    parser.add_argument("--chat", action="store_true", help="Interactive multi-turn chat")
    parser.add_argument("--list-models", action="store_true", help="List models available from the chosen provider")
    parser.add_argument("--provider", choices=list(advisor.PROVIDERS), help="AI provider (default: AI_PROVIDER in .env, else ollama)")
    args = parser.parse_args()

    try:
        if args.provider:
            advisor.set_provider(args.provider)
        if args.list_models:
            for m in advisor.list_models():
                print(f"{m['id']:<55} {m['context'] or '':>9}  {m['name']}")
            return 0

        if args.recommendations:
            recs, model = advisor.get_recommendations(args.brand, args.category, args.count)
            print(json.dumps(recs, indent=2, ensure_ascii=False))
            print(f"\n[model: {model}]", file=sys.stderr)
            return 0

        if args.chat:
            history: list[dict] = []
            print("MarketPulse AI marketing advisor. Type 'exit' to quit.\n")
            while True:
                try:
                    q = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 0
                if q.lower() in {"exit", "quit"}:
                    return 0
                if not q:
                    continue
                answer, model = advisor.get_advice(q, args.brand, history)
                history += [{"role": "user", "content": q}, {"role": "assistant", "content": answer}]
                print(f"\nAdvisor ({model}):\n{answer}\n")

        question = " ".join(args.question) or "What are the top 3 marketing opportunities in this market right now?"
        answer, model = advisor.get_advice(question, args.brand)
        print(answer)
        print(f"\n[model: {model}]", file=sys.stderr)
        return 0
    except advisor.AdvisorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
