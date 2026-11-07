"""MarketPulse in-app assistant: the chat algorithm behind POST /ai/chat.

Each turn:
  1. Detect the intent of the message (chart analysis, ideas, campaign, copy, ...).
  2. Pre-compute statistics for every chart the page sent (min/max/mean/trend/leader),
     because small local models are unreliable at arithmetic over raw rows.
  3. Build the prompt: role + intent-specific format + page context + chart data/stats
     + market data snapshot + trimmed history + the user's message.
  4. Stream the answer back (advisor.stream_chat).
"""
from __future__ import annotations

import json
from statistics import mean

import advisor

MAX_CHART_ROWS = 40
MAX_CHART_CHARS = 7000
HISTORY_CHAR_BUDGET = 6000

INTENTS = [
    # (name, keywords, instruction appended to the system prompt)
    ("chart_analysis", ["analy", "chart", "graph", "trend", "explain this", "what does this show", "insight", "spike", "drop", "pattern"],
     "TASK: Analyse the chart(s). Structure: **What it shows** (1 line) → **Key findings** (3-5 bullets, each citing a number "
     "from the Facts) → **Why it matters** for marketing → **Recommended actions** (2-3 concrete actions)."),
    ("campaign", ["campaign", "launch", "promotion", "promo"],
     "TASK: Design one campaign: concept, key message, target segment, channels, week-by-week timeline, budget split and KPIs."),
    ("calendar", ["calendar", "schedule", "content plan", "posting plan"],
     "TASK: Produce a content calendar as a Markdown table: Day | Channel | Format | Topic/Hook | Call to action."),
    ("copy", ["slogan", "tagline", "headline", "caption", "copy", "ad text", "email subject", "hook"],
     "TASK: Write 8 copy options, varied in style, each under 15 words. Mark your top 3 and say why in one line each."),
    ("competitor", ["competitor", "compare", " vs", "versus", "against", "rival", "benchmark"],
     "TASK: Compare the brands/products head to head using the data: a short Markdown table of key metrics, "
     "then strengths, weaknesses and the best attack/defence move for the brand in focus."),
    ("sentiment", ["sentiment", "complain", "review", "negative", "feedback", "customers say", "people say"],
     "TASK: Analyse customer sentiment: top positive and negative drivers (with scores), root causes, and messaging fixes."),
    ("summary", ["summar", "overview", "tl;dr", "tldr", "brief", "report"],
     "TASK: Give an executive summary: 3 headline insights with numbers, 1 risk, 1 opportunity, and next steps."),
    ("ideas", ["idea", "suggest", "brainstorm", "how can", "how do i", "how should", "grow", "improve", "strategy", "recommend"],
     "TASK: Give 5 marketing ideas ranked from quickest win to biggest impact. For each: **name**, what to do, "
     "the data point that justifies it, cost (low/medium/high) and one KPI."),
]

SYSTEM_PROMPT = (
    "You are MarketPulse AI, the assistant built into the MarketPulse market-intelligence dashboard. "
    "You help a marketing team analyse the dashboard's charts and turn them into marketing ideas, campaigns, copy and plans. "
    "Ground everything in the data provided: cite concrete numbers. Never invent metrics that are not in the data; "
    "if something is not in the data, say so. Be concise and use Markdown (short headings, bullets, tables when useful)."
)


def detect_intent(message: str, focus_chart: bool) -> tuple[str, str]:
    if focus_chart:
        return INTENTS[0][0], INTENTS[0][2]
    text = f" {message.lower()} "
    for name, keywords, instruction in INTENTS:
        if any(k in text for k in keywords):
            return name, instruction
    return "general", ""


# ----------------------------------------------------------------------------- chart facts
TIME_KEYS = {"month", "week", "date", "day", "period", "time", "year", "quarter"}


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _fmt(v):
    return f"{v:,.0f}" if abs(v) >= 1000 else (f"{v:g}" if isinstance(v, float) else str(v))


def chart_facts(rows: list[dict]) -> tuple[str, list[str]]:
    """Turn chart rows into plain-language, pre-computed facts.

    Small local models are unreliable at arithmetic and at reading raw JSON, so the
    numbers they should quote (rankings, gaps, % changes, peaks) are computed here.
    Returns (kind, facts) where kind is "time series", "categories" or "records".
    """
    rows = [r for r in rows if isinstance(r, dict)]
    if not rows:
        return "records", []
    label_key = next((k for k, v in rows[0].items() if isinstance(v, str)), None)
    numeric = [k for k in rows[0] if k != label_key and any(_num(r.get(k)) is not None for r in rows)]
    if not label_key or not numeric:
        return "records", []
    facts = []
    if label_key.lower() in TIME_KEYS and len(rows) > 1:
        first_label, last_label = rows[0][label_key], rows[-1][label_key]
        for key in numeric:
            pts = [(r[label_key], _num(r.get(key))) for r in rows if _num(r.get(key)) is not None]
            if len(pts) < 2:
                continue
            (l0, v0), (l1, v1) = pts[0], pts[-1]
            hi, lo = max(pts, key=lambda p: p[1]), min(pts, key=lambda p: p[1])
            change = f", {(v1 - v0) / abs(v0) * 100:+.1f}%" if v0 else ""
            facts.append(f"{key}: {_fmt(v0)} ({l0}) -> {_fmt(v1)} ({l1}){change}; peak {_fmt(hi[1])} ({hi[0]}), low {_fmt(lo[1])} ({lo[0]}).")
        latest = {k: _num(rows[-1].get(k)) for k in numeric if _num(rows[-1].get(k)) is not None}
        if len(latest) > 1:
            ranked = sorted(latest.items(), key=lambda kv: kv[1], reverse=True)
            facts.append(f"Ranking at {last_label}: " + ", ".join(f"{k} {_fmt(v)}" for k, v in ranked) + ".")
            earliest = {k: _num(rows[0].get(k)) for k in latest if _num(rows[0].get(k))}
            if earliest:
                growth = {k: (latest[k] - earliest[k]) / abs(earliest[k]) * 100 for k in earliest}
                fastest = max(growth, key=growth.get)
                facts.append(f"Fastest growth {first_label} -> {last_label}: {fastest} ({growth[fastest]:+.1f}%).")
        return "time series", facts
    for key in numeric:
        pts = [(r[label_key], _num(r.get(key))) for r in rows if _num(r.get(key)) is not None]
        if not pts:
            continue
        ranked = sorted(pts, key=lambda p: p[1], reverse=True)
        line = f"Ranking by {key} (one value per {label_key}): " + ", ".join(f"{n} {_fmt(v)}" for n, v in ranked) + "."
        if len(ranked) > 1:
            line += (f" Highest: {ranked[0][0]} ({_fmt(ranked[0][1])}); lowest: {ranked[-1][0]} ({_fmt(ranked[-1][1])});"
                     f" gap {_fmt(round(ranked[0][1] - ranked[-1][1], 2))}; average {_fmt(round(mean(v for _, v in pts), 1))}.")
        facts.append(line)
    return "categories", facts


def _clean_rows(rows) -> list[dict]:
    """Drop styling-only fields (colors) and cap row count."""
    def keep(k, v):
        if k in ("color", "tone", "fill", "icon", "id") or isinstance(v, (dict, list)):
            return False
        return not (isinstance(v, str) and v.startswith(("#", "var(")))

    return [{k: v for k, v in r.items() if keep(k, v)} for r in (rows or [])[:MAX_CHART_ROWS] if isinstance(r, dict)]


def _chart_text(chart: dict, include_data: bool) -> tuple[str, str]:
    rows = _clean_rows(chart.get("data"))
    kind, facts = chart_facts(rows)
    lines = [f"### {chart.get('title')} ({kind})"]
    if chart.get("subtitle"):
        lines.append(f"Description: {chart['subtitle']}")
    if chart.get("note"):
        lines.append(f"Note: {chart['note']}")
    if facts:
        lines.append("Facts (pre-computed, exact):\n" + "\n".join(f"- {f}" for f in facts))
    if include_data or not facts:
        lines.append("Data: " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
    return kind, "\n".join(lines)


def charts_block(charts: list[dict], focus: str | None) -> tuple[str, str | None]:
    """Returns (text, kind of the focused chart or None)."""
    if not charts:
        return "", None
    focused = next((c for c in charts if c.get("id") == focus), None)
    if focused:
        kind, text = _chart_text(focused, include_data=True)
        others = [c.get("title") for c in charts if c is not focused]
        extra = f"\n(Other charts on this page: {', '.join(others)}.)" if others else ""
        return "THE CHART TO ANALYSE:\n" + text + extra, kind
    parts, used = [], 0
    for c in charts:
        _, text = _chart_text(c, include_data=used < MAX_CHART_CHARS)
        parts.append(text)
        used += len(text)
    return "CHARTS ON THE USER'S CURRENT PAGE:\n\n" + "\n\n".join(parts), None


CHART_GUIDANCE = {
    "categories": "This chart has exactly ONE value per category - talk about the ranking, the leader, the laggard and the gap. "
                  "Do NOT invent trends, highs/lows or changes for individual categories.",
    "time series": "This is a time series - talk about each line's direction and % change, its peak, who leads at the latest "
                   "point and who is growing fastest.",
    "records": "These are individual records (mentions/reviews) - group them into themes and note sentiment and engagement.",
}


def _trim_history(history: list[dict]) -> list[dict]:
    kept, total = [], 0
    for m in reversed(history or []):
        if m.get("role") not in ("user", "assistant") or not m.get("content"):
            continue
        total += len(m["content"])
        if total > HISTORY_CHAR_BUDGET:
            break
        kept.append({"role": m["role"], "content": m["content"]})
    kept.reverse()
    while kept and kept[0]["role"] == "assistant":
        kept.pop(0)
    return kept


def build_messages(message: str, history: list[dict], brand: str | None, page: dict | None,
                   charts: list[dict], focus_chart: str | None) -> tuple[str, list[dict]]:
    intent, instruction = detect_intent(message, bool(focus_chart))
    brand = None if brand in (None, "", "All brands") else brand
    page = page or {}
    filters = page.get("filters") or {}
    charts_text, focus_kind = charts_block(charts, focus_chart)
    if focus_kind:
        instruction += " " + CHART_GUIDANCE[focus_kind]
    rule = "Quote numbers exactly as written in the Facts/data; never compute or invent new ones."
    # Order matters for small models: background first, the task last (closest to the answer).
    context = [
        SYSTEM_PROMPT,
        # A focused chart analysis gets only that chart, so the model cannot mix in other numbers.
        None if focus_kind else "MARKET DATA SNAPSHOT (background, JSON):\n" + advisor.build_context(advisor.load_market_data(), brand),
        f"USER IS VIEWING: {page.get('title', 'dashboard')} ({page.get('path', '/')}). "
        f"Active filters: brand={filters.get('brand', 'All brands')}, range={filters.get('range', '30d')}, "
        f"source={filters.get('source', 'All sources')}." + (f" Focus on {brand}." if brand else ""),
        charts_text,
        f"{instruction} {rule}".strip(),
    ]
    messages = [{"role": "system", "content": "\n\n".join(p for p in context if p)}]
    messages += _trim_history(history)
    messages.append({"role": "user", "content": message})
    return intent, messages


def stream_answer(message: str, history=None, brand=None, page=None, charts=None, focus_chart=None):
    """Return (intent, generator of text chunks). Raises AdvisorError before streaming if the model is unavailable."""
    intent, messages = build_messages(message, history or [], brand, page, charts or [], focus_chart)
    gen = advisor.stream_chat(messages, temperature=0.5)
    first, model = next(gen)  # surface connection/model errors before the HTTP response starts

    def chunks():
        yield first
        for text, _ in gen:
            yield text

    return intent, model, chunks()
