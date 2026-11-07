# INVESTIGATION — AI Marketing Strategist & Data Analyst (2026-11-07, read-only, Opus 5)

Read-only investigation for the next product step: turn the existing "Ask AI" assistant into a full
AI Marketing Strategist & Data Analyst. No code was changed, no commit was made, no service was started.
CONFIRMED = ran it or read the exact line, output shown; UNVERIFIED = inferred, not proven; NOT DONE = skipped, and why.

§1 reproduces the user's requirement list in full, rendered in English from the Romanian original (meaning
preserved, not a literal translation); every point is treated as a requirement in §2–§5. The user's own
Romanian wording is quoted where the exact phrasing matters.

---

## 0. Answer in five lines

A working assistant already exists and is better than a generic chatbot: it streams Markdown, receives the
**real rows** of every chart on the page, pre-computes exact facts (rankings, peaks, % change, gaps) so a small
model cannot do arithmetic wrong, and is grounded in the live MySQL API. What it is **not**: it has no tools,
no structured strategy template, no anomaly/correlation analysis, no UI control, no citations, no persistence,
and its grounding silently falls back to a **stale static snapshot** — measured below, the live assistant
answered with snapshot numbers (24% segment share, sensitivity 82) while the dashboard showed 37.5% and 0.0.
The gap is therefore not "connect an LLM" (done) but "give the LLM a controlled tool layer, a module
architecture, and an honest missing-data policy". Recommended first delivery: orchestrator + tool registry +
typed SSE + permanent panel (Phase 0), then Chart Intelligence v2 and the Strategy Generator, which together
are the visible transformation. 10 numbered questions for the user are in §7.

---

## 1. The problem as reported (the user's full requirement list)

> "I'd take the MarketPulse AI chatbot much further than a simple assistant that answers questions. I'd turn it
> into an AI Marketing Strategist & Data Analyst — a virtual consultant that can interpret market data, explain
> the dashboard's visualisations, and build argued marketing strategies. The user should not just look at charts,
> but be able to discuss with the app what those charts mean and what decisions they could take from them."

The user then enumerated six blocks. Each is a requirement, reproduced here so nothing is lost:

**1. Identity.** Three competences in one assistant: *marketing strategist* (strategies, campaigns),
*data analyst* (interprets data and charts), *market researcher* (trends, competitive opportunities).
Explicitly **not** a generic chatbot that says "post more often on Instagram" — it must analyse the company,
product, consumer and competitor context before recommending.

**2. Modules.**
- **A. Marketing Strategy Generator (priority).** Full strategy for a product/brand: Market Research,
  Target Audience, Segmentation, Positioning, SWOT, Marketing Mix (4P), Campaign Strategy, Budget Allocation,
  KPIs, Timeline. Must explain **why** each recommendation and **which data** supports it.
- **B. Chart Intelligence (priority).** Explain any dashboard chart: (1) what it represents, (2) overall trend,
  (3) max/min, (4) unusual fluctuations, (5) factors that could explain the evolution *if data supports them*,
  (6) marketing implications, (7) actions. Must also answer: "why did positive sentiment drop?", "which brand
  has the best perception?", "which product has the most negative reviews?", "how do price and rating
  correlate?", "what trends in the last 30 days?". Must receive the **real data, not an image**.
- **C. Consumer Intelligence.** Preferences, segmentation, purchase drivers, recurring complaints, liked
  features, comparison between consumer categories. Example: "why do users prefer Apple over Samsung?" —
  grouped on ecosystem, design, performance, price, user experience.
- **D. Competitor Intelligence.** Brand comparison: positioning, price differences, consumer perception,
  competitive advantages, weaknesses from reviews, differentiation opportunities.
- **E. Campaign & Content Generator.** Campaign ideas, ad messages, slogans, social content, editorial
  calendar, influencer collaborations, launch campaigns, loyalty campaigns.

**3. How it should think.** Not just a model wired to a chat box: a system giving the model *controlled access*
to MarketPulse information. Components named by the user: *AI Orchestrator* (understands the question, selects
tools), *Analytics Engine*, *Marketing Engine*, *Data Retrieval*, *Consumer Intelligence*, *Grounded AI Response*.
Technology table proposed by the user: AI Orchestrator Python, API FastAPI, LLM "OpenAI API or other compatible
model", Data Analysis Pandas/NumPy, ML Scikit-learn, NLP Transformers, Database PostgreSQL, Context retrieval
SQL + eventual RAG, Frontend React. Explicit: **do not train a model from scratch** — use an existing LLM
connected to MarketPulse data and functions.

**4. Advanced features.** (1) Marketing Opportunity Detection, (2) Predictive Marketing Insights (with an
explicit uncertainty warning), (3) Automated SWOT, (4) Customer Persona Generator, (5) Marketing KPI Advisor
(CTR, Conversion Rate, CAC, ROAS, Engagement Rate, Customer Retention Rate), (6) What-if Analysis
("what if I cut the price 10%?") — using historical data or **explicit assumptions**, never presented as certainty.

**5. UI repositioning.** "Let's rethink the chatbot position so it is somehow more permanent, maybe on the right
in a small window from top to bottom as a chat, with all the skills and tools needed to do everything **+ interact
directly with the platform and control it**: show tabs, help, explain fully, control everything to help the user."
And explicitly: **"the Ask AI button that opens an overlay window is super practical — we'll keep it while
extending with all these things."**

**6. Streaming.** Wants streamed output, nicely formatted (rendered Markdown: headings, lists, bold, tables).
The brief asks to check what exists in `src/components/AssistantChat.jsx` and `src/services/api.js` and say what
is missing for smooth streaming (incremental rendering, typing cursor, tables, code).

**Deadline for this spec:** 19:30 today. Implementation is a separate, later decision.

---

## 2. Measured findings

### 2.1 What the assistant is today (CONFIRMED — every line read)

| Piece | File:line | What it actually does |
|---|---|---|
| Separate FastAPI app | `backend/server.py:17-24` | A **second** app, not `main.py`. Own CORS regex, own port (started on 8020 on this machine). |
| Chat endpoint | `backend/server.py:125-141` | `POST /ai/chat`, streams `text/plain`, headers `X-Intent`, `X-Model`. |
| Advice endpoint | `backend/server.py:144-150` | `POST /ai/advice`, non-streaming. **No caller in `src/`** (only `askMarketingAdvisor` in `api.js:171-180`, itself unused). |
| Recommendations endpoint | `backend/server.py:100-113` | `GET /analytics/recommendations`, 10-minute in-process cache. Not called by the frontend. |
| Request contract | `backend/server.py:116-122` | `message, history, brand, page{path,title,filters}, charts[{id,title,subtitle,data,note}], focusChart`. |
| Intent detection | `backend/assistant.py:22-43`, `:53-60` | **Keyword substring matching** over 9 intents (`chart_analysis, campaign, calendar, copy, competitor, sentiment, summary, ideas`), first match wins, `general` fallback. No model, no tools. |
| System prompt | `backend/assistant.py:45-50` | "You are MarketPulse AI… ground everything in the data provided… never invent metrics." |
| Chart facts | `backend/assistant.py:75-120` | Deterministic stats: time series → first→last with % change, peak, low, ranking at the last point, fastest growth; categories → ranking, highest/lowest, gap, average. |
| Chart block | `backend/assistant.py:133-163` | Focused chart gets **full rows**; other charts get facts and, while the character budget allows, rows. Caps: `MAX_CHART_ROWS=40`, `MAX_CHART_CHARS=7000` (`:18-20`). |
| Chart guidance | `backend/assistant.py:166-172` | Per-kind instruction (categories → ranking only, no invented trends; time series → direction/peak/leader; records → themes). |
| Prompt assembly | `backend/assistant.py:190-214` | system prompt + market snapshot (omitted when a chart is focused, `:204`) + page/filters + charts + task + "quote numbers exactly" (`:199`) + trimmed history (`:175-187`, 6000 chars). |
| Streaming | `backend/assistant.py:217-228` → `backend/advisor.py:314-383` | Provider-agnostic SSE reader; yields `(delta, model)` per chunk (`advisor.py:375-377`); models tried in order. |
| Providers | `backend/advisor.py:33-59` | openrouter (default), groq, gemini, ollama. One key drives every surface (`:79-86`). |
| Live grounding | `backend/advisor.py:117-182` | Fetches 6 endpoints from the main API (`/api/analytics/overview`, `/brands`, `/products`, `/consumer-segments`, `/sentiment`, `/competitors`) and reshapes them. |
| Snapshot fallback | `backend/advisor.py:185-207` | Any exception → `backend/market_data.json`, `source: "snapshot"`, **only a `logger.warning`** (`:133`). |
| Context builder | `backend/advisor.py:210-233` | JSON of kpis, brands, brandStats, products, segments, sentiment aspects/keywords/reviews, mentions. |
| Frontend panel | `src/components/AssistantChat.jsx:73-157` | Floating panel, open/close, quick actions, 6 chart chips, send/stop/reset. |
| Chart registration | `src/context/ChatContext.jsx:5-16`, `:46-55`, `:58-61` | External store keyed by chart title slug; `ChartCard data={...}` and `<ChartData/>` register rows. |
| Chart "Analyse" button | `src/components/common.jsx:36-41` | `askAssistant('Analyse the "X" chart', id)` → opens panel and sends. |
| HTTP client | `src/services/api.js:145-169` | `streamAssistantChat` accumulates the full text and calls `onText(fullText)` on **every** chunk. |
| Mount point | `src/components/Layout.jsx:115` | `<AssistantChat pageTitle pagePath />` inside the app shell. |

**Intent coverage vs the five modules.** `campaign`, `calendar`, `copy`, `competitor`, `sentiment`, `summary`,
`ideas` exist as *prompt formats only* (`assistant.py:27-42`). There is no strategy template, no SWOT, no
persona, no what-if, no KPI advisor, no opportunity detection, no prediction. `chart_analysis` is the only
intent with real computation behind it.

**No tool layer.** `grep` for `tools|tool_choice|function_call|tool_calls` across `assistant.py`, `advisor.py`,
`server.py` returns nothing. The model cannot ask for a calculation; it gets one fixed prompt and answers.

### 2.2 What data exists for grounding (CONFIRMED — endpoints called, output read)

| Endpoint (main API, 8010) | Returns | Live volume on this machine |
|---|---|---|
| `GET /api/analytics/overview` (`api/analytics.py:46-52`) | kpis, evolution (12 weekly points × 5 brands), mentions (6), topMovers (4), counts | 10 products, 48 reviews, sentiment 76.1, 5 brands |
| `GET /api/analytics/sentiment` (`:55-121`) | distribution, weekly trend, aspects, keywords (12), 50 newest reviews, total | 48 reviews, 3 sources |
| `GET /api/analytics/brands` (`:124-136`) | share of voice, mentions, sentiment, health, topics, concerns | 5 brands |
| `GET /api/analytics/consumer-segments` (`:139-144`) | 5 segments: size, users, spend, loyalty, sensitivity, preferences | 5 segments |
| `GET /api/analytics/competitors` (`:147-153`) | brands, price differences vs category median, 6-feature matrix, activity | 10 price rows |
| `GET /api/analytics/recommendations` (`:168-275`) | executive summary + rule-based InsightCards | derived engine + optional LLM |
| `GET /api/analytics/trends` (`:357-424`) | TrendMetric rows or derived scores | — |
| `GET /api/analytics/prices?product_id` (`:327-354`) | current/min/max/avg/change | — |
| `GET /api/marketing/trends` (`api/marketing.py:97-224`) | weekly per brand/source, 3 opportunities, 4 KPIs, source volume | — |
| `GET /api/products/` (`api/products.py:115-175`) | cards with sentiment, change, interest, pros/cons | 10 products |
| `GET /api/products/compare?ids` (`:178-219`) | 2–4 cards | — |
| `GET /api/products/{id}` (`:222-319`) | card + price history + linear forecast + 20 reviews + review summary | — |
| `GET /api/products/{id}/prices`, `/reviews` (`:468-493`) | raw rows | — |

**Derivations available as Python functions** (`backend/services/analytics_service.py`): sentiment 0-100
(`:100-118`), price change (`:120-130`), interest (`:132-139`), aspect breakdown (`:141-167`), pros/cons
(`:169-187`), brand stats (`:204-269`), evolution series (`:271-314`), keyword cloud (`:316-350`), sentiment
trend (`:352-386`), distribution (`:388-400`), consumer segments (`:406-485`), competitor dashboard (`:491-568`),
marketing trends (`:574-614`), source volume (`:616-623`), rule-based recommendations (`:629-780`), overview
(`:786-891`). Price forecasting is linear regression over stored points (`services/forecasting.py:57-105`).

**Scale matters for the architecture:** 10 products, 48 reviews, 5 brands, 3 sources. The entire dataset fits
in a prompt many times over. This is not a retrieval problem today — see §4.6.

### 2.3 Gap analysis per module (each gap with `file:line`)

#### A. Marketing Strategy Generator — **does not exist**

| Required section | What exists | Gap |
|---|---|---|
| Market research | `overview` KPIs, `evolution_series`, `marketing_trends` | No demand/market-size data at all; must be framed as "what the platform observes", not market research |
| Target audience | `consumer_segments` (`analytics_service.py:406-485`) | Segment definitions are **rule-assigned by aspect membership** (`:429-444`), not survey clusters; the assistant must say so |
| Segmentation | same | No demographic or behavioural dimensions beyond aspects and price |
| Positioning | `competitor_dashboard` (`:491-568`) price vs category median | No perceptual map input beyond aspect scores |
| SWOT | nothing | No generator anywhere |
| Marketing mix 4P | product cards (price, specs, pros/cons), `source_volume` | "Place" has no channel data; "Promotion" has no spend data |
| Campaign strategy | `campaign` intent prompt (`assistant.py:27-28`) | Free-form paragraph; no structure, no data references |
| Budget allocation | nothing | No spend data; only a declared allocation model is honest |
| KPIs | nothing | No campaign metrics exist (see §2.7) |
| Timeline | `calendar` intent (`assistant.py:29-30`) | Content calendar only, no strategy timeline |
| "Why + which data" | `assistant.py:199` ("quote numbers exactly") | No per-section evidence requirement, no citation mechanism |

#### B. Chart Intelligence — **partially exists, 4 of 7 sub-questions missing**

| Requirement | Status | Evidence |
|---|---|---|
| 1. What the chart represents | Partial | Only `title`, `subtitle`, `note` (`assistant.py:136-140`); no metric definition (e.g. what "indexed to 100" means) |
| 2. Overall trend | **Yes** | `chart_facts` first→last + % change (`:90-109`) |
| 3. Max/min | **Yes** | peak/low per series (`:97-99`) |
| 4. Unusual fluctuations | **No** | No z-score, no change-point, no outlier flag anywhere in the repo |
| 5. Factors that explain the evolution | **No** | No correlation, no cross-series join, no price↔sentiment linkage |
| 6. Marketing implications | Prompt only | `assistant.py:25-26` |
| 7. Actions | Prompt only | `assistant.py:25-26` |
| "Why did positive sentiment drop?" | **No** | Needs per-week aspect deltas; `sentiment_trend` (`analytics_service.py:352-386`) returns only positive/neutral/negative shares |
| "Which brand has the best perception?" | Partial | `brand_stats` has it, but in focus mode the market snapshot is **deliberately omitted** (`assistant.py:204`) |
| "Which product has the most negative reviews?" | **No** | No ranked negative-review aggregate exists |
| "How do price and rating correlate?" | **No** | No correlation function |
| "What trends in the last 30 days?" | **No** | The `range` filter is UI-only — see §2.7 |
| Real data, not an image | **Yes** | Rows are sent (`ChatContext.jsx:46-55`, `assistant.py:133-145`) |
| Silent truncation | Risk | `MAX_CHART_ROWS=40` / `MAX_CHART_CHARS=7000` (`assistant.py:18-20`) drop rows without telling the model |

#### C. Consumer Intelligence — **data exists, evidence assembly does not**

| Requirement | Status | Gap |
|---|---|---|
| Preferences | Partial | `preferences` per segment (`analytics_service.py:464-469`) is the segment description + top-2 aspects |
| Segmentation | **Yes** | `consumer_segments` (`:406-485`) |
| Purchase drivers | Partial | Aspect scores only (`:141-167`); no weighting, no stated influence |
| Recurring complaints | Partial | `pros_cons` (`:169-187`) and `concerns` (`:251-255`) at brand level only |
| Liked features | **Yes** | `pros` (`:169-187`) |
| Compare preferences between segments | **No** | No per-segment aspect breakdown exposed; `aspect_breakdown(group)` is computed inside the segment loop (`:465`) but not returned |
| "Why Apple over Samsung?" | **No** | No head-to-head review retrieval by brand pair |

#### D. Competitor Intelligence — **data exists, narrative does not**

| Requirement | Status | Gap |
|---|---|---|
| Positioning | Partial | Price vs category median (`:502-522`), aspect matrix (`:526-541`) |
| Price differences | **Yes** | `priceDifferences` (`:510-522`) |
| Consumer perception | **Yes** | sentiment + health per brand (`:232-266`) |
| Competitive advantages | Partial | `topics` (`:247-250`) |
| Weaknesses from reviews | Partial | `concerns` (`:251-255`) |
| Differentiation opportunities | **No** | No generator; `_derived_opportunities` (`api/marketing.py:23-82`) is market-level, not brand-pair |
| Marketing-strategy comparison | **No** | No channel/spend/campaign data exists |

#### E. Campaign & Content Generator — **prompt formats only**

| Requirement | Status | Gap |
|---|---|---|
| Campaign ideas | Prompt | `campaign` intent (`assistant.py:27-28`) |
| Ad messages / slogans | Prompt | `copy` intent (`:31-32`) |
| Social content | Prompt | same |
| Editorial calendar | Prompt | `calendar` intent (`:29-30`), Markdown table |
| Influencer proposals | **No** | No influencer data anywhere |
| Launch campaigns | Prompt | same as campaign |
| Loyalty campaigns | **No** | No retention/loyalty data (the segment `loyalty` field is a sentiment score, `analytics_service.py:480`) |
| Budget / KPI targets | **No** | No campaign metrics |

### 2.4 Advanced features (all six)

| # | Feature | Today | What is missing |
|---|---|---|---|
| 1 | Marketing Opportunity Detection | `_derived_opportunities` (`api/marketing.py:23-82`) → 3 cards; `recommendations` (`analytics_service.py:629-780`) → rule signals | Not conversational; no ranking by expected impact; no product-level opportunities; no "why now" |
| 2 | Predictive Insights | `forecast_next_period` (`forecasting.py:57-105`), used only for the product drawer (`api/products.py:266-275`) | No uncertainty band, no sentiment forecast, no explicit "estimate, not certainty" labelling in chat |
| 3 | Automated SWOT | Nothing | Generator + evidence mapping (S/W from aspects, O/T from competitor gaps) |
| 4 | Customer Persona Generator | Segments only (`analytics_service.py:406-485`) | Persona synthesis from segment + review language; **no demographics exist** |
| 5 | Marketing KPI Advisor | Nothing | KPI catalogue + measurement plan; **no CTR/CAC/ROAS data exists** (§2.7) |
| 6 | What-if Analysis | Nothing | Arithmetic scenario engine + explicit assumptions; no elasticity data |

### 2.5 UI and streaming — what exists, what is missing

**Panel today** (`src/styles/global.css:835-893`): launcher bottom-right (`:835`), panel
`position: fixed; right: 24px; bottom: 24px; width: min(440px, calc(100vw - 32px)); height: min(680px, calc(100vh - 48px))`
(`:838`), full-screen under 760px (`:891-893`). Open state lives in `ChatContext.jsx:23`; Escape closes it
(`AssistantChat.jsx:88-93`). It is **not** permanent and does not survive a reload.

**Markdown renderer** (`AssistantChat.jsx:25-70`):
- supported: `#`–`####` headings (all rendered as `<h4>`), pipe tables with a separator row, ordered and
  unordered lists with **one** nesting level, inline `**bold**`, `*italic*`, `_italic_`, `` `code` ``;
- **missing**: fenced code blocks (` ``` `), links `[text](url)`, blockquotes, horizontal rules, images,
  tables without a header row, escaped pipes, multi-level nesting, task lists.

**Streaming path** (`api.js:148-169` → `AssistantChat.jsx:111`):
- the server **is** incremental (`advisor.py:375-377` yields per delta);
- the client accumulates and calls `onText(fullText)` on **every** chunk (`api.js:160-167`);
- React then re-renders and **re-parses the entire Markdown tree** on every chunk (`AssistantChat.jsx:148`),
  which is O(n²) work for a long strategy answer;
- there is a "thinking" dots indicator (`AssistantChat.jsx:147`) but **no typing cursor**, no throttle, no
  incremental block parsing;
- auto-scroll fires on every message change (`:87`), so a user scrolling up is yanked back down.

**Nothing else exists**: no conversation persistence (`messages` is `useState([])`, `AssistantChat.jsx:77`),
no citations, no actions, no copy button, no token/usage display, no error taxonomy beyond a red bubble.

### 2.6 Grounding defect found during this investigation (CONFIRMED, with the numbers)

This is the most important finding for the new architecture.

- The **dashboard** reads live MySQL: `GET /api/analytics/overview` returned `10` products, `48` reviews,
  sentiment `76.1`; `GET /api/analytics/consumer-segments` returned Value optimizers `37.5%`, sensitivity `0.0`.
- The **assistant** answered `GET http://127.0.0.1:8020/analytics/recommendations?category=Marketing` with
  *"Value optimizers represent 24% of the market with high price sensitivity (82)"*.
- `24%` and `82` are exactly the values in `backend/market_data.json` (snapshot segments:
  `Performance seekers 28%/34, Value optimizers 24%/82, …`), **not** the live values.
- Mechanism: `advisor.load_market_data()` (`advisor.py:185-207`) falls back to the snapshot on any exception
  and only logs a warning (`:133`). The response carries `source: "snapshot"`, but nothing in the prompt or the
  UI surfaces it, so the user cannot tell which source answered.
- Second, independent defect in the same path: the live dict (`advisor.py:136-182`) has **no**
  `exampleRecommendations` key, but `get_recommendations` indexes it unconditionally (`advisor.py:451`). A
  *successful* live fetch would therefore raise `KeyError`. Both branches are wrong; the endpoint is not used
  by the frontend (the page calls the main API's `/api/analytics/recommendations`).

Consequence for this feature: **grounding must be explicit and visible**. Every answer must carry which
source produced each number, and a fallback must be a labelled degradation, not a silent substitution.

### 2.7 What the platform does NOT have (hard constraints on honest answers)

These are not bugs to fix in this feature; they are facts the assistant must respect and state.

| Missing input | Consequence |
|---|---|
| Impressions, clicks, conversions, campaign spend | **CTR, Conversion Rate, CAC, ROAS cannot be computed.** Only "recommended KPI + how to measure it" is honest. |
| Demographics (age, gender, income, location) | Personas can only be inferred from review language; must be labelled as inferred. |
| Market size / TAM / growth rates | "Market research" is limited to what the platform observes. |
| Competitor spend / channel mix | No marketing-strategy comparison between brands. |
| Influencer data | Influencer proposals are creative suggestions, not data-backed. |
| Price elasticity / demand curve | What-if is an arithmetic scenario with stated assumptions, not a prediction. |
| A working date-range filter | `filters.range` exists in `AppContext.jsx:4` and `FilterBar.jsx:15`, but **no API call passes it** (`api.js:53-61` only forwards brand/source/category; the backend has no `range` parameter). "Last 30 days" cannot be answered today. |
| Source filter beyond sentiment | `filters.source` reaches only `/api/analytics/sentiment` (`api.js:102-106`); `/brands`, `/overview`, `/consumer-segments`, `/competitors` ignore it. |
| Any campaign or conversion event | Every KPI in §2.4 #5 is a recommendation, never a measurement. |

### 2.8 Operational facts (CONFIRMED)

- The three services are up right now: main API `8010` (`{"status":"online","database":"healthy","llm":"configured"}`),
  assistant `8020` (`{"ok":true,"provider":"openrouter","key_configured":true}`), frontend `5173` (HTTP 200).
- The assistant service process started at `2026-11-07 17:38:05`, i.e. **after** `advisor.py` was last modified
  (17:31), so it is running the current code.
- **The launcher does not start the assistant.** `scripts/start.ps1:117-118` starts only `main:app`;
  `run.ps1` only reads `VITE_AI_API_URL` (`:203`). The setup scripts ask for the assistant port
  (`scripts/setup.ps1:311`, `settings.ps1:277`) but nothing launches it. A user who runs `run.ps1` gets a
  dashboard whose "Ask AI" button fails with "Cannot reach the AI backend".
- **No assistant tests exist.** `backend/tests/` has no file mentioning `assistant` or `advisor`;
  `e2e/` has no test mentioning the assistant, "Ask AI" or `/ai/chat`.

---

## 3. Every module the change would touch (each read)

### 3.1 Backend — existing files

| File | Lines that matter | Why it is touched |
|---|---|---|
| `backend/assistant.py` | `:22-43` intents, `:45-50` prompt, `:53-60` detection, `:75-120` facts, `:148-163` chart block, `:190-214` assembly, `:217-228` stream | Becomes the *prompt/format* layer behind the orchestrator; intent detection is replaced by planning |
| `backend/advisor.py` | `:33-59` providers, `:117-182` live fetch, `:185-207` fallback, `:210-233` context, `:314-383` stream, `:448-480` recommendations | Provider + streaming stay; `load_market_data`/`build_context` are replaced by tools; `:451` must be fixed or removed |
| `backend/server.py` | `:100-150` routes | Either mounted into `main.py` or kept as a compatibility shim |
| `backend/main.py` | `:60-64` routers | Include the new AI router so one process serves everything |
| `backend/config.py` | `:50-68` OpenRouter, `:72-75` AI provider | New settings (fast model, deep model, tool budget, guard on/off) |
| `backend/services/analytics_service.py` | `:100-891` | Add: correlation, anomaly flags, ranked negative reviews, per-segment aspects, per-week aspect deltas |
| `backend/services/forecasting.py` | `:57-105` | Add residual/uncertainty band for predictive insights |
| `backend/services/llm_service.py` | `:170-270` `complete()` | Reused for non-streaming structured calls (SWOT, personas) with the existing cache |
| `backend/api/analytics.py` | `:46-424` | New endpoints for the computations above |
| `backend/api/marketing.py` | `:23-82` opportunities | Reused as an opportunity source |
| `backend/api/products.py` | `:115-319` | Reused for product detail and evidence |

### 3.2 Backend — new files (proposed)

| File | Purpose |
|---|---|
| `backend/ai/orchestrator.py` | Intent → plan → tools → facts → prompt → stream; the only place that decides what to call |
| `backend/ai/tools.py` | The tool registry: one function per capability, each returning `{data, source, coverage}` |
| `backend/ai/marketing_engine.py` | Pure functions: SWOT, 4P skeleton, budget split, KPI plan, persona synthesis, what-if arithmetic |
| `backend/ai/prompts.py` | One template per module (strategy, chart, consumer, competitor, campaign), each demanding evidence per section |
| `backend/ai/guard.py` | Number audit, missing-data policy, action extraction, citation assembly |
| `backend/api/ai.py` | `POST /api/ai/chat` (SSE), `GET /api/ai/capabilities`, `GET /api/ai/health` |

### 3.3 Frontend — existing files

| File | Lines | Why it is touched |
|---|---|---|
| `src/components/AssistantChat.jsx` | `:25-70` renderer, `:73-157` panel | Permanent layout, streaming cursor, code blocks, links, citations, action buttons, persistence |
| `src/context/ChatContext.jsx` | `:5-16` store, `:21-32` provider, `:46-61` registration | Add UI command bus + conversation persistence; keep the chart store byte-compatible |
| `src/context/AppContext.jsx` | `:4` filters, `:15-17` updateFilter | Expose filters to the assistant's action runner |
| `src/services/api.js` | `:145-169` stream, `:171-180` advice | New SSE parser; keep `streamAssistantChat` signature or migrate callers |
| `src/components/Layout.jsx` | `:115` mount | Panel layout: main column offset, persistent panel, keep launcher |
| `src/styles/global.css` | `:835-893` | Panel geometry, cursor, citations, action chips, mobile behaviour |
| `src/components/common.jsx` | `:36-41` ChartCard | Keep `data` registration; add chart id/definition metadata |
| `src/pages/*.jsx` | local state (see §3.4) | Register controllable state for the action runner |
| `e2e/pages.spec.js`, `e2e/smoke.spec.js` | — | New tests for the panel, streaming, actions |
| `backend/tests/test_api.py` | — | Contract tests for the new endpoints |

### 3.4 Page-level state that a controlling assistant would need (each read)

| Page | State | Line |
|---|---|---|
| `MarketOverview.jsx` | none (global filters only) | — |
| `ProductAnalysis.jsx` | `sortKey`, `sortDirection`, `category`, `selectedId` (drawer), `compareIds`, `tableQuery` | `:14-19` |
| `BrandIntelligence.jsx` | `selectedBrands`, `focusBrand` | `:12-13` |
| `SentimentAnalysis.jsx` | `page`, `sentimentFilter` | `:14-15` |
| `ConsumerInsights.jsx` | `activeSegment` | `:16` |
| `MarketingAnalytics.jsx` | `activeMetric` | `:16` |
| `CompetitorAnalysis.jsx` | none | — |
| `AIRecommendations.jsx` | `category` | `:12` |

All of it is **local `useState`**, unreachable from outside the page. Global state is only
`filters` + `theme` (`AppContext.jsx:7-8`) and the chart store (`ChatContext.jsx:5-16`).

---

## 4. Options, with evidence

### 4.1 Where the orchestrator lives

| Option | What changes | Evidence / trade-off |
|---|---|---|
| **A. Keep two services** | Add tools to `server.py` that call the main API over HTTP | The hop already exists and already fails silently (`advisor.py:133`); two processes, two ports, and the launcher starts neither the second one nor its `VITE_AI_API_URL` |
| **B. Mount into `main.py`** | New `api/ai.py` router; tools use SQLAlchemy directly | One process, one port, real transactions, no snapshot fallback, the launcher already runs it (`scripts/start.ps1:117`) |
| **C. Hybrid** | Router in `main.py`; `server.py` re-exports the same app for compatibility | Same as B, plus nothing breaks for anyone starting `server:app` |

**Recommendation: C.** It removes the silent-fallback class of bug by construction and makes the assistant
start with the app the user already runs.

### 4.2 How the model gets data

| Option | How | Trade-off |
|---|---|---|
| A. Prompt stuffing (today) | One prompt with the whole context | Works at 48 reviews; no freshness guarantee; grows without bound |
| B. Native function calling | Model emits tool calls, loop until done | Needs provider support; free models vary; each round trip costs latency and tokens |
| C. Deterministic planner | Rules pick 2–6 tools, one LLM call writes the answer | Fast, cheap, predictable, testable; less open-ended |
| D. Hybrid | Planner for the 5 modules; function calling for open questions | Best of both; more code |

**Recommendation: D, delivered as C first.** The planner is what makes the five modules reliable; function
calling is an opt-in later. Reason: the configured free model is a reasoning model whose tool support cannot be
assumed, and a failed tool loop is a 30-second dead end for the user.

### 4.3 How the assistant controls the UI

| Option | Mechanism | Trade-off |
|---|---|---|
| A. URL only | `navigate(path)` via React Router | Safe, tiny, no page changes; cannot open a drawer or select a segment |
| B. Full command bus | Pages register handlers; assistant dispatches | Maximum control; touches all 8 pages; risk of acting on stale state |
| C. Declarative actions | Response carries a typed action list; one runner executes a fixed vocabulary | Auditable, testable, no page coupling until a page opts in |

**Recommendation: C, phased.** Phase 1 vocabulary: `navigate`, `set_filter`, `highlight_chart` (no page
changes). Phase 2: `open_product`, `select_segment`, `set_page_tab` (each page registers a handler). Destructive
actions are never in the vocabulary.

### 4.4 Streaming protocol

| Option | Trade-off |
|---|---|
| A. `text/plain` (today) | Simplest; cannot carry actions, citations or coverage |
| B. SSE with typed events | One connection, named events, works with the existing `getReader()` loop; needs a small parser |
| C. NDJSON | Same as B but a non-standard content type for this use |

**Recommendation: B.** Events: `meta`, `token`, `action`, `citation`, `done`, `error`. Keep `text/plain`
behind `?format=text` for one release so nothing breaks.

### 4.5 Model and latency

- The configured model is `dots-studio/dots-3-note-preview:free` with `reasoning.effort=high`
  (`config.py:53`, `:66`). The project's own notes record a reasoning model taking 15–100 s and a 50-second
  endpoint looking broken (WORKING-NOTES IX.4).
- A permanent panel makes latency **visible on every question**, not just on a page load.

| Option | Trade-off |
|---|---|
| A. One model, progress state | Simplest; every chart question waits for a reasoning model |
| B. Two-tier | Fast model for chart/consumer/competitor Q&A; deep model for strategy/SWOT/what-if, behind a visible "Deep analysis" toggle |
| C. Fast model everywhere | Cheapest latency; weakest strategy output |

**Recommendation: B**, with the tier printed in the message header so the user knows which answered.

### 4.6 RAG or SQL

At 10 products / 48 reviews, the whole corpus is smaller than a single prompt. A vector store would add a
dependency, an index to keep fresh, and a new failure mode for zero retrieval benefit.

**Recommendation: SQL now.** Add `search_reviews(query, brand, aspect, limit)` using SQL `LIKE` + the existing
stopword list (`analytics_service.py:48-62`). Revisit embeddings only when review volume makes prompt stuffing
impossible; the tool interface makes that a drop-in change later.

### 4.7 Conversation persistence

| Option | Trade-off |
|---|---|
| A. None (today) | A reload loses everything |
| B. `localStorage` | No schema change, survives reload, per-browser |
| C. DB table | Survives devices; needs a migration, a user identity, and a retention policy |

**Recommendation: B now, C only if the user asks for cross-device history.**

### 4.8 Technology table reconciliation

The user's table lists PostgreSQL, Pandas, NumPy, Scikit-learn, Transformers, "OpenAI API". The project's
standing decisions (WORKING-NOTES I.7) are **MySQL** and **OpenRouter**. Reconciliation:

- **Database stays MySQL.** Switching would contradict a standing decision and gains nothing at this size.
- **LLM stays OpenRouter** (free tier, 1000 RPD). "OpenAI-compatible" is already true: `advisor.py` speaks the
  OpenAI chat API to four providers.
- **Pandas / NumPy / Scikit-learn / Transformers: not needed.** Every computation in §2.2 is 5–50 lines of
  plain Python over lists; the repo deliberately removed pandas/numpy/scikit-learn because nothing imported
  them (`backend/requirements.txt:36`). Adding them back for `mean` and `sorted` is weight without capability.
- **RAG: not now** (§4.6).

---

## 5. Recommendation (precise)

### 5.1 Target architecture

```
Browser (React)
  AssistantChat — permanent right panel, launcher kept
    sends : message, history, page{path,title,filters}, charts[], focusChart, uiState
    reads : SSE  meta | token | action | citation | done | error
        │
        ▼
FastAPI — main.py, port 8010 (one process)
  POST /api/ai/chat  (text/event-stream)
        │
        ▼
  AI Orchestrator  (backend/ai/orchestrator.py)
    1. classify   → module + required tools        (rules; optional LLM router)
    2. call tools → SQLAlchemy → MySQL             (backend/ai/tools.py)
    3. engines    → analytics / marketing / consumer / competitor
    4. facts      → exact numbers + source + coverage per field
    5. prompt     → module template + facts + page context + gaps
    6. stream     → advisor.stream_chat (provider-agnostic)
    7. guard      → number audit, missing-data policy, action extraction
```

**Why this shape:** it keeps everything that already works (chart rows, pre-computed facts, streaming,
provider abstraction, OpenRouter key) and adds only the missing layer — a controlled tool surface with
explicit provenance. Nothing in the current prompt logic is removed; `chart_facts` becomes one tool among many.

### 5.2 Tool catalogue (the implementer's contract)

Every tool returns `{ "data": ..., "source": "table|endpoint", "coverage": {field: "measured|derived|not_collected"} }`.

| # | Tool | Input | Returns | Grounding |
|---|---|---|---|---|
| 1 | `market_overview` | — | kpis, counts, top movers | `analytics_service.overview` |
| 2 | `brand_stats` | `brand?` | share, sentiment, health, topics, concerns | `:204-269` |
| 3 | `list_products` | `brand?, category?, search?` | cards | `api/products.py:115` |
| 4 | `product_detail` | `id \| name` | card, price history, forecast, reviews | `:222-319` |
| 5 | `price_history` | `product_id` | points, min/max/avg/change | `forecasting.py:14-55` |
| 6 | `sentiment` | `brand?, product_id?, source?` | distribution, trend, aspects, keywords | `api/analytics.py:55-121` |
| 7 | `review_evidence` | `query?, brand?, product_id?, aspect?, limit?` | matching review snippets | **new** — SQL LIKE |
| 8 | `segments` | — | 5 segments with all fields | `:406-485` |
| 9 | `segment_aspects` | `segment_id` | aspect scores **for that segment** | **new** — expose `:465` |
| 10 | `competitors` | — | brands, price diffs, matrix | `:491-568` |
| 11 | `marketing_trends` | — | weekly series, source volume | `:574-623` |
| 12 | `recommendations` | `category?` | rule signals | `:629-780` |
| 13 | `chart` | `chart_id` | the chart the user is looking at | request payload |
| 14 | `compute` | `metric, group_by, filter` | one aggregation (avg price by brand, count by source, correlation price↔rating, sentiment by month) | **new** |
| 15 | `anomalies` | `series` | z-score flags, change points | **new** |
| 16 | `forecast` | `series, periods` | projection + residual band | `forecasting.py:57-105` + **new** band |
| 17 | `swot` | `brand \| product` | 4 quadrants, each with evidence | **new** |
| 18 | `persona` | `segment_id` | persona + inferred-only label | **new** |
| 19 | `budget_split` | `total, goal` | allocation model with stated rules | **new**, declared model |
| 20 | `kpi_plan` | `goal, channels` | recommended KPIs + measurement plan | **new**, no invented values |
| 21 | `what_if_price` | `product_id, pct` | scenario arithmetic + assumptions | **new** |
| 22 | `opportunities` | `brand?` | ranked opportunities | `api/marketing.py:23-82` + **new** ranking |

UI actions are **not** server-side tools; they are emitted as `action` events with a fixed vocabulary:
`navigate(path)`, `set_filter(key, value)`, `highlight_chart(id)`, `open_product(id)`, `select_segment(id)`,
`set_page_tab(page, tab)`.

### 5.3 Anti-hallucination design (the part that makes this trustworthy)

1. **Facts block.** Every tool output is flattened into a `FACTS` section with exact numbers and the source of
   each. The prompt says: cite only these numbers.
2. **Number audit (`backend/ai/guard.py`).** After streaming, extract every numeric token from the answer,
   normalise (thousands separators, `%`, currency, `x`), and check membership in the facts set. Report
   `ungrounded_numbers` in the `done` event; the UI shows "N numbers could not be traced to the data". One
   automatic regeneration is allowed; a second failure is shown, not hidden.
3. **Coverage policy.** Each module declares the fields it needs. Fields the platform does not collect
   (§2.7) are listed in a `GAPS` block; the prompt instructs: *state the gap in one line, then continue with
   what is available; never estimate silently.*
4. **Source labels.** Each fact carries `source`; the UI renders a citation chip (`Brands · /api/analytics/brands`).
5. **No fabricated campaign metrics.** A fixed list (`CTR, conversion, CAC, ROAS, spend, impressions`) is
   answered as "not collected by this platform" plus a measurement plan — never as a number.
6. **Temperature policy.** Analysis 0.2–0.3; creative (copy, slogans) 0.7; strategy 0.4.
7. **Deterministic engines first.** SWOT, budget split, what-if and KPI plans are computed in Python; the LLM
   only *writes them up*. The numbers never come from the model.

### 5.4 UI design

- **Permanent panel, right side, full height.** `position: fixed; top: 0; right: 0; bottom: 0; width: clamp(360px, 26vw, 460px)`.
  The main column gets `margin-right` equal to the panel width when open, so nothing is covered. Below 1100px it
  becomes an overlay drawer; below 760px full screen (the existing rule at `global.css:891-893` already does this).
- **Keep the floating "Ask AI" launcher** — the user explicitly asked to keep it. It opens/restores the panel;
  the panel stays open across navigation and survives a reload (state in `localStorage`).
- **Header:** title, model tier badge (Fast / Deep), context chips (page · brand · focused chart), new-chat,
  collapse.
- **Skill rail:** five module buttons (Strategy, Charts, Consumers, Competitors, Campaigns) + six advanced
  actions (Opportunities, SWOT, Persona, KPIs, What-if, Forecast). Each inserts a prepared prompt scoped to the
  current page and brand.
- **Messages:** streamed Markdown with a typing cursor; tables, fenced code, links; citation chips under each
  answer; action buttons ("Show me") that execute the emitted action; a small footer with `tools used`,
  `source`, `ungrounded numbers`.
- **Composer:** textarea, send/stop, "Deep analysis" toggle, clear conversation.
- **Accessibility:** `role="complementary"`, `aria-live="polite"` on the message list (already present at
  `AssistantChat.jsx:139`), focus trap when overlay, Escape closes only the overlay.

### 5.5 Delivery order and effort

Ordered so that each phase is shippable on its own and the visible product improves at every step.
Sizes are implementer-days, gate included (pytest + build + Playwright, §III.1).

| Phase | Scope | Size | Why this order |
|---|---|---|---|
| **0. Foundation** | Orchestrator skeleton, tool registry (tools 1–13), SSE protocol, permanent panel, persistence, number audit, one process (`main.py`) | **L — 3.5 d** | Everything else plugs into it; also fixes the silent-snapshot defect by construction |
| **1. Chart Intelligence v2** | Tools 14–16, anomaly flags, correlation, per-week aspect deltas, chart definitions, `range` wiring, "why" evidence | **M — 2 d** | Highest visible payoff; the user's example is a chart question |
| **2. Strategy Generator** | 10-section template, evidence per section, budget split, KPI plan, timeline | **M — 2 d** | The named priority; depends on 0 and benefits from 1 |
| **3. Consumer Intelligence** | Tool 9, `review_evidence`, segment comparison, "why Apple over Samsung" | **M — 1.5 d** | Data already exists; mostly assembly |
| **4. Competitor Intelligence** | Head-to-head evidence, differentiation opportunities | **M — 1.5 d** | Data already exists |
| **5. Campaign & Content** | Campaign/calendar/copy templates with data references, launch vs loyalty | **M — 1.5 d** | Reuses 2's template machinery |
| **6. Advanced A** | SWOT, personas, opportunity ranking | **M — 2 d** | Needs 3 and 4 |
| **7. Advanced B** | Predictive with uncertainty, what-if, KPI advisor | **M — 2 d** | Needs 1 and 2 |
| **8. UI control** | `navigate` + `set_filter` (phase 1), then page actions (phase 2) | **M — 2 d** | Independent; can run in parallel with 3–7 |

**Demo cut (if time is short):** Phase 0 + 1 + 2 + the `navigate`/`set_filter` half of 8 ≈ **8 days** gives the
visible transformation: a permanent strategist panel that explains any chart with real numbers, writes a full
strategy with evidence, and moves the user around the app.

**Total:** ≈ 18 implementer-days for everything, plus review/verification per PR.

### 5.6 What NOT to build

- No vector database, no embeddings, no RAG at 48 reviews (§4.6).
- No pandas/numpy/scikit-learn/transformers (§4.8).
- No PostgreSQL migration (§4.8).
- No model training or fine-tuning (the user said so explicitly).
- No fabricated campaign metrics, demographics, market size or elasticity (§2.7).
- No autonomous actions: the assistant proposes, the user clicks. The only auto-executed actions are
  `navigate` and `highlight_chart`.

---

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | Reasoning-model latency (15–100 s) makes a permanent panel feel broken | Two-tier models (§4.5), first-token progress, streamed output, visible tier badge |
| 2 | The model quotes a number that is not in the facts | Number audit (§5.3.2), `ungrounded_numbers` surfaced in the UI, one regeneration |
| 3 | The assistant answers with stale snapshot data (measured in §2.6) | One process, tools read MySQL directly, no snapshot fallback in the chat path; a labelled degradation if the DB is down |
| 4 | Free-tier limits (1000 RPD) exhausted by a chatty panel | Existing `llm_cache` (`llm_service.py:130-164`), per-tool caching, a visible quota state, no automatic retry storms |
| 5 | The assistant invents campaign metrics because the user asked for CAC/ROAS | Hard-coded unsupported-metric list (§5.3.5) + a contract test that asserts the refusal |
| 6 | UI actions act on stale page state | Actions carry a page path; the runner ignores an action whose page is not mounted; no destructive verbs |
| 7 | Streaming re-parses the whole Markdown per chunk (today's O(n²)) | Incremental block parsing + 60 ms throttle + a cursor (§5.4) |
| 8 | The panel covers the dashboard on small screens | `margin-right` on the main column, drawer below 1100px, full screen below 760px |
| 9 | A new endpoint drifts from the frontend contract (the historical failure mode, WORKING-NOTES IX.4) | Extend `backend/tests/test_api.py` (the contract suite) with the new endpoints and the SSE event shapes |
| 10 | The tool layer becomes a second business-logic copy of `analytics_service` | Tools call the service functions; they never re-implement a metric |

---

## 7. QUESTIONS for the user

Fiecare întrebare are o recomandare. Răspunde „toate recomandările" dacă ești de acord cu toate.

1. **Ce livrăm primele?** Există cinci module mari. Le facem pe rând, iar primele două ar fi
   *Chart Intelligence* (explicarea graficelor) și *Strategy Generator* (strategia completă), pentru că sunt
   cele pe care le vei vedea imediat în demo. Alternativa e să începem cu Consumer + Competitor, care au deja
   datele pregătite și ies mai repede. — **Rec: Chart Intelligence, apoi Strategy Generator.** Sunt exact cele
   două pe care le-ai numit prioritare, iar restul se sprijină pe ele.

2. **Cât control vrei să aibă asistentul asupra aplicației?** Trei trepte: (a) doar navighează între pagini;
   (b) navighează + schimbă filtrele (brand, sursă); (c) controlează și elementele din pagini — deschide fișa
   unui produs, selectează un segment, schimbă tabul unui grafic. (c) atinge toate cele 8 pagini și cere mai mult
   timp de testare. — **Rec: (b) acum, (c) imediat după.** Navigarea și filtrele dau 80% din senzația de
   „control", fără să rescriem fiecare pagină.

3. **Ce model folosim pentru răspunsuri?** Modelul configurat acum este un model de raționament care poate
   gândi 15–100 de secunde înainte să răspundă — într-un panou permanent asta se simte ca o aplicație blocată.
   Opțiuni: (a) păstrăm un singur model; (b) două trepte — un model rapid pentru întrebări pe grafice și modelul
   de raționament doar pentru strategii, cu buton „Analiză profundă"; (c) model rapid peste tot. —
   **Rec: (b).** Răspunsurile simple apar în câteva secunde, iar analizele grele rămân de calitate.

4. **Ce face asistentul când nu are datele necesare?** De exemplu, dacă îl întrebi de CTR, CAC sau ROAS —
   platforma nu colectează campanii, deci nu are cum să știe. Opțiuni: (a) spune clar „platforma nu colectează
   asta" și oferă ce se poate calcula; (b) dă o estimare etichetată ca estimare; (c) refuză întrebarea. —
   **Rec: (a).** Este singura variantă care nu inventează cifre și rămâne utilă.

5. **Acceptăm librării noi?** Tabelul tău propune Pandas, NumPy, Scikit-learn, Transformers, PostgreSQL.
   La volumul actual (10 produse, 48 de recenzii) toate calculele se fac în câteva linii de Python simplu, iar
   proiectul le-a eliminat anterior intenționat. — **Rec: nu adăugăm niciuna acum.** MySQL rămâne baza
   (decizie deja luată), LLM rămâne OpenRouter. Dacă datele cresc, adăugăm atunci.

6. **Cum trimitem răspunsul către interfață?** Acum e text simplu, ceea ce înseamnă că asistentul nu poate
   trimite butoane, acțiuni sau surse. Opțiuni: (a) rămânem la text simplu; (b) evenimente tipizate (SSE) care
   pot transporta și text, și acțiuni, și surse. — **Rec: (b).** Fără asta nu există „arată-mi tabul" sau
   „deschide produsul".

7. **Păstrăm conversația după refresh?** Opțiuni: (a) nu (ca acum — se pierde la reload); (b) în browser
   (`localStorage`), fără modificări de bază de date; (c) în baza de date, disponibilă pe orice dispozitiv. —
   **Rec: (b).** Ieftin, fără migrare, suficient pentru demo și pentru utilizare zilnică.

8. **Panoul: permanent sau flotant?** Ai cerut permanent, în dreapta, de sus până jos, dar și păstrarea
   butonului „Ask AI". Opțiuni: (a) panou permanent + butonul păstrat (butonul deschide/restaurează panoul);
   (b) doar flotant, ca acum, dar mai mare; (c) permanent fără buton. — **Rec: (a).** Este exact ce ai descris.

9. **Ce facem cu datele care lipsesc structural?** Platforma nu are deloc: demografice (vârstă, venit, oraș),
   mărime de piață, bugete de campanie, date despre influenceri, elasticitatea prețului. Opțiuni: (a) asistentul
   le declară necolectate și propune un plan de măsurare; (b) extindem platforma ca să le colecteze (proiect
   separat, mult mai mare); (c) inventăm valori plauzibile pentru demo. — **Rec: (a).** (c) contrazice regula
   „niciun placeholder prezentat ca produs".

10. **Bugetul de apeluri și modelul.** Contul are ~1000 cereri/zi pe modelul gratuit. Un panou permanent poate
    consuma repede. Opțiuni: (a) cache agresiv + un model rapid pentru chat + modelul de raționament doar la
    cerere; (b) fără cache, toate cererile pe modelul de raționament; (c) alt model gratuit, ales de tine. —
    **Rec: (a).** Și, dacă vrei alt model, spune-mi id-ul exact și îl punem în configurare.

---

## 8. CONFIRMED / UNVERIFIED / NOT DONE

**CONFIRMED (read the exact line, or ran it and saw the output):**
- The assistant is a separate FastAPI app on 8020 with 6 routes (`server.py:40-150`); the main API on 8010 is
  a different app (`main.py:44-64`).
- Intent detection is keyword substring matching over 9 intents (`assistant.py:22-60`); there is no tool layer
  anywhere (`grep` for `tools|tool_choice|function_call|tool_calls` → 0 hits).
- Chart rows are sent to the backend (`ChatContext.jsx:46-55` → `assistant.py:133-145`), and exact facts are
  pre-computed (`assistant.py:75-120`).
- Live data volumes: 10 products, 48 reviews, 5 brands, 3 sources, 5 segments (endpoints called, output read).
- **The assistant answered with snapshot numbers** (24%, sensitivity 82) while the dashboard showed live values
  (37.5%, 0.0) — the snapshot file contains exactly 24% and 82. Cause of the fallback is UNVERIFIED (§2.6).
- `advisor.py:451` indexes `data["exampleRecommendations"]`, a key the live dict does not have (`:136-182`).
- The `range` filter is UI-only: `AppContext.jsx:4`, `FilterBar.jsx:15`, and no API call passes it
  (`api.js:53-61`).
- The launcher starts only `main:app` and npm (`scripts/start.ps1:117-118`, `:152`); nothing starts the
  assistant service.
- No assistant tests exist in `backend/tests/` or `e2e/`.
- The Markdown renderer supports headings, pipe tables, one-level lists, inline bold/italic/code
  (`AssistantChat.jsx:25-70`); it has no fenced code blocks, links, blockquotes or rules.
- Streaming is incremental server-side (`advisor.py:375-377`) but the client re-renders the whole Markdown per
  chunk (`api.js:160-167`, `AssistantChat.jsx:148`).
- All three services are up right now (8010, 8020, 5173), and the assistant process started at 17:38:05,
  after `advisor.py` was last modified at 17:31.

**UNVERIFIED:**
- Why `_live_market_data()` fell back to the snapshot at the moment of the probe (the endpoints answer in
  <0.1 s now, so the failure was transient or environmental — e.g. a proxy variable in the service's
  environment; not established).
- Whether the configured free model supports native function calling. Not probed (would be a live call).
- The actual first-token latency of the configured model on this machine. Not measured (no chat call made
  beyond the incidental one below).
- Whether `dots-studio/dots-3-note-preview:free` is still available and free at the time of implementation.

**NOT DONE:**
- No code changed, no commit, no branch, no service started or stopped.
- No live external call of my own. **Disclosure:** one incidental OpenRouter generation happened because the
  read-only probe `GET http://127.0.0.1:8020/analytics/recommendations?category=Marketing` generated and cached
  recommendations server-side. Budget used: **1 call**. No other external call was made.
- No RAG, no embeddings, no library installation, no database change.

---

## 9. Left on disk

- `.orchestration/specs/004-ai-strategist-chatbot.md` — this file, the only thing written.
- Nothing else created, deleted or modified. No processes started; the three running services were only read
  with GET requests and left exactly as found.

by FiredMosquito831

## USER DECISIONS (2026-11-07 17:51, binding)

Utilizatorul a răspuns: **„all rec"** — acceptă toate cele 10 recomandări din acest spec.

Deciziile rezultate, în ordinea în care se implementează:

1. **Q1 — Prioritatea modulelor.** B (Chart Intelligence) primul, apoi A (Strategy), apoi E (Campaign), apoi C și D împreună.
2. **Q2 — Amplasarea panoului.** Ambele: overlay flotant implicit, plus un control „pin to side" în header. Butonul Ask AI existent rămâne neschimbat.
3. **Q3 — Controlul platformei.** Nivel (b): acțiuni declarative, pe whitelist, randate ca chips-uri și executate doar la click-ul utilizatorului. Niciodată execuție directă de către model.
4. **Q4 — Model și latență.** Modelul free rămâne implicit; un toggle „Deep reasoning" per cerere comută pe un model mai puternic pentru planificare și strategie. Niciodată blocarea UI-ului.
5. **Q5 — Date lipsă.** Se afișează „Not enough data" și se numește ce lipsește. Niciodată 0, niciodată o cifră inventată.
6. **Q6 — Librării noi.** Niciuna pentru acum. Agregatele se calculează în SQL și în stdlib. MySQL rămâne.
7. **Q7 — Streaming.** Randare îmbogățită: append pe delta, cursor de typing, blocuri de cod, linkuri, citări, tabele bufferizate, buton de copiere.
8. **Q8 — Persistența conversației.** Rămâne de confirmat din textul întrebării; se aplică recomandarea agentului.
9. **Q9 — Comportamentul pe eroare.** Fallback la modelul free, cu etichetă vizibilă în UI.
10. **Q10 — Ordinea de livrare.** Cele trei felii din §5.4, cea mai mică prima.

**Consecință:** implementarea începe cu feliile 0 și 1. Restul intră în QUEUE.md.

by FiredMosquito831
