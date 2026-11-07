# INVESTIGATION — AI Marketing Strategist chatbot (2026-11-07, read-only, Opus 5)

Written from the user's verbatim requirements, quoted in full in §1. Nothing outside `.orchestration/` was edited. No live LLM call was made while writing this. CONFIRMED = read the exact line or ran the command, output shown; UNVERIFIED = inferred from reading, not executed; NOT DONE = skipped, and why.

## 0. Answer in five lines

The chat **exists and works**: a floating "Ask AI" panel (`src/components/AssistantChat.jsx`), a streaming endpoint (`backend/server.py:125`), intent detection and pre-computed chart facts (`backend/assistant.py`), and a small Markdown renderer (`AssistantChat.jsx:25-70`). It is a **single-shot Q&A over the current page's charts**, not the strategist the user describes: no orchestrator/tool selection, no strategy generator with the ten required components, no SWOT/persona/KPI/what-if/opportunity modules, no platform control, no conversation persistence, and chart intelligence only sees charts mounted on the page the user is on. The gap is therefore **not a rewrite of the chat** but **five new capabilities behind one orchestrator**, plus three UI upgrades (formatted streaming, optional dock, declarative actions). Recommended delivery in three slices (§5.4), smallest first, each independently shippable and each provable against live MySQL. Ten questions in §7, each with a recommendation; "all rec" accepts every one.

## 1. The problem as reported (verbatim from the user)

> „Da! Eu aș duce chatbot-ul MarketPulse AI mult mai departe decât un simplu asistent care răspunde la întrebări. L-aș transforma într-un AI Marketing Strategist & Data Analyst, adică un consultant virtual care poate interpreta datele pieței, explica vizualizările din dashboard și construi strategii de marketing argumentate.
>
> Practic, utilizatorul nu ar trebui doar să vadă niște grafice, ci să poată discuta cu aplicația despre ceea ce înseamnă acele grafice și ce decizii ar putea lua pe baza lor."

> „Nu vreau să fie un chatbot generic care oferă răspunsuri de tipul „postează mai des pe Instagram". Trebuie să analizeze contextul companiei, produsului, consumatorilor și concurenței înainte să ofere recomandări."

> „Important: chatbot-ul trebuie să primească datele reale din grafic, nu doar o imagine a acestuia. Astfel, poate face calcule și interpreta valorile corect."

> „Aici este partea cea mai importantă: nu este suficient să conectăm un model AI la un câmp de chat. Trebuie să construim un sistem care îi oferă acces controlat la informațiile MarketPulse AI."

> „De asemenea să regândim puțin poziția chatbotului să fie cumva mai permanent, poate pus în dreapta într-un mic window de sus până jos sub formă de chat, să aibă toate skill-urile și uneltele necesare pentru a putea face tot + interacționa direct cu platforma și a o și controla: arată tab-uri, ajută, explică full, să poată controla tot pentru a ajuta user-ul și oferi totul posibil."

> „BTW amplasarea cu buton pentru Ask AI care deschide un window over e super practică, super mișto — o vom păstra în timp ce extindem cu toate aceste chestii."

> „vom vrea să vedem output cu streaming în agent frumos formatat."

The five modules (A–E), the six advanced features, the architecture table and the technology table the user listed are reproduced verbatim in §4.1–§4.3 so no requirement is lost in paraphrase.

## 2. Measured findings — what already exists

### 2.1 The chat surface — CONFIRMED

| What | Where | State |
|---|---|---|
| Floating launcher "Ask AI" | `src/components/AssistantChat.jsx:131` | exists, `aria-label`, fixed bottom-right (`src/styles/*.css:835`) |
| Overlay panel | `AssistantChat.jsx:132-157`, CSS `:838` | exists, `role="dialog"`, `aria-label`, Esc to close (`:88-93`) |
| Header (avatar, title, "Sees N charts on <page>") | `AssistantChat.jsx:133-138` | exists |
| New conversation | `AssistantChat.jsx:136` (`reset`, `:126`) | exists — clears React state only |
| Stop generation | `AssistantChat.jsx:153` (`stop`, `:125`) | exists — `AbortController` |
| 6 quick actions | `AssistantChat.jsx:12-22` | exists |
| Per-chart "Analyse" list | `AssistantChat.jsx:143` | exists, driven by registered charts |
| Message list, `aria-live="polite"` | `AssistantChat.jsx:139-150` | exists |
| Intent + model badge | `AssistantChat.jsx:148` | exists (`X-Intent`, `X-Model`) |
| Minimal Markdown (bold/em/code/headings/lists/tables) | `AssistantChat.jsx:25-70` | exists — see §2.4 for what it cannot render |
| Streaming transport | `src/services/api.js:148-169` | exists — `response.body.getReader()`, `onText(fullText, meta)` |
| Chart registration store | `src/context/ChatContext.jsx:5-16`, `:46-55`, `:58-61` | exists — external store, no re-render |
| "Analyse" button → chat request | `ChatContext.jsx:26-29` (`askAssistant`) | exists, used by every `ChartCard` |

### 2.2 The backend — CONFIRMED

| What | Where | State |
|---|---|---|
| `POST /ai/chat` streaming | `backend/server.py:125-141` | exists; `StreamingResponse`, `text/plain`, `X-Intent`/`X-Model` headers |
| `ChatRequest` shape | `backend/server.py:116-122` | `message, history, brand, page{path,title,filters}, charts[], focusChart` |
| Intent detection | `backend/assistant.py:53-60`, table `:22-43` | **keyword matching** over 8 intents |
| Pre-computed chart facts | `backend/assistant.py:75-120` | exists — time-series/categories/records, rankings, peaks, % change |
| Chart → prompt | `backend/assistant.py:133-163` | exists; focused chart gets raw data, others get facts |
| Prompt assembly | `backend/assistant.py:190-214` | exists; background first, task last |
| History trimming | `backend/assistant.py:175-187` | exists, 6000-char budget, last 12 turns at the endpoint |
| Streaming from provider | `backend/advisor.py:314-383` | exists; SSE parse, model fallback, errors before first chunk |
| Market data for grounding | `backend/advisor.py:185-207` | exists; live API (MySQL) preferred, JSON snapshot fallback, `source` marked |
| Compact context builder | `backend/advisor.py:210-233` | exists; KPIs, brands, products, segments, aspects, keywords, reviews, mentions |
| Recommendation engine | `backend/advisor.py:448-482`, `server.py:100-113` | exists; 13 cards, 4 categories, 600 s cache |
| `POST /ai/advice` (non-streaming) | `backend/server.py:144-150` | exists; used by `askMarketingAdvisor` (`api.js:171-180`) — **no caller in `src/`** (UNVERIFIED: grep found none) |
| DB tables | `backend/database/models.py:18,62,77,106,122` | `products`, `price_history`, `reviews`, `trend_metrics`, `llm_cache` |

### 2.3 What does **not** exist — the real gap

1. **No orchestrator.** "Intent" is a keyword table (`assistant.py:53-60`). There is no tool selection, no multi-step plan, no ability to ask the analytics engine for a computation the prompt did not already contain. The user's §3 architecture (AI Orchestrator → Analytics Engine / Marketing Engine / Data Retrieval / Consumer Intelligence → Grounded Response) has no counterpart in code.
2. **No Marketing Strategy Generator.** The `campaign` intent (`assistant.py:27-28`) asks for "one campaign: concept, key message, target segment, channels, week-by-week timeline, budget split and KPIs". The user's module A requires **ten** components: Market Research, Target Audience, Segmentation, Positioning, SWOT, Marketing Mix (4P), Campaign Strategy, Budget Allocation, KPIs, Timeline — plus an explicit "why this strategy and which data supports it".
3. **No Consumer Intelligence module.** `build_context` (`advisor.py:221`) passes `consumerSegments` as raw JSON; there is no preference extraction, no complaint clustering, no cross-category comparison, no "why Apple over Samsung" analysis grounded in reviews.
4. **No Competitor Intelligence module.** The `competitor` intent (`assistant.py:33-35`) asks for a table + strengths/weaknesses. There is no positioning map, no price-gap analysis, no review-derived weakness extraction, no differentiation-opportunity output.
5. **No Campaign & Content Generator beyond one campaign.** `copy` (`:31-32`) gives 8 copy options; `calendar` (`:29-30`) gives a table. There are no campaign *ideas* ranked, no influencer proposals, no retention campaigns, no structured objective/audience/message/channel/budget/calendar/KPI block.
6. **No advanced features.** Opportunity Detection, Predictive Insights, Automated SWOT, Persona Generator, KPI Advisor, What-if — none exist as code paths. (The dashboard's `/api/analytics/recommendations` is a different, card-based feature.)
7. **Chart Intelligence is page-scoped and shallow.** Only charts mounted on the current page register (`ChatContext.jsx:49-53`). The assistant cannot answer "compare this month's sentiment chart with the one on the brands page", cannot see a chart the user is not looking at, and cannot fetch a series the page did not render. The user explicitly asks for chart ID + indicator + time range + actual data + filters — the first two and the last are absent from `ChatRequest` (`server.py:116-122` has `charts[]` and `filters`, no indicator/range contract).
8. **No conversation persistence.** `messages` is `useState` (`AssistantChat.jsx:77`); reload or route change loses everything. "New conversation" is the only lifecycle control.
9. **No platform control.** The assistant cannot navigate, open a drawer, apply a filter, switch a tab, or focus a chart. `askAssistant` exists but is only invoked by the user clicking "Analyse".
10. **Streaming is correct but the render is not fluid.** See §2.4.
11. **No tests.** `grep -rn "assistant\|/ai/chat" backend/tests/*.py` returned **zero matches** (CONFIRMED). The whole assistant stack — `assistant.py`, `advisor.stream_chat`, `/ai/chat` — is untested by the gate.
12. **Small model.** `/health` reports `dots-studio/dots-3-note-preview:free` (CONFIRMED via `GET 127.0.0.1:8020/health`). Free-tier, rate-limited, and weak at arithmetic — which is exactly why `chart_facts` pre-computes numbers. Any reasoning-heavy module (strategy, SWOT, what-if) will need a stronger model or a deterministic pre-computation layer.

### 2.4 Streaming: what is missing for "frumos formatat" — CONFIRMED

The transport is already token-streaming. The **render** is the problem:

- `AssistantChat.jsx:34-70` re-parses the **entire accumulated string** on every chunk, and React re-renders the whole message subtree. Cost is O(n²) in answer length and the DOM is rebuilt each token. No memoisation, no incremental block parsing.
- No typing cursor. `chat-typing` (`:878-881`) only covers the *pre-first-token* state; once text arrives there is no visual "still writing" affordance.
- `inline()` (`:25-32`) handles `**bold**`, `` `code` ``, `*em*`, `_em_`. It does **not** handle links `[text](url)`, strikethrough, or nested emphasis.
- `Markdown()` (`:34-70`) handles `#`–`####` (all rendered as `<h4>`), tables, ordered/unordered lists with **one** nesting level, and paragraphs. It does **not** handle fenced code blocks ```` ``` ````, blockquotes, horizontal rules, or links. A model that emits a code block or a link shows raw backticks/URLs.
- Tables render only when the row matches `/^\s*\|.*\|\s*$/`; a table whose first row is still streaming is shown as paragraphs until the closing pipe arrives, then snaps into a table (visible layout jump).
- There is no "copy answer" control, no token/latency indicator, no error affordance beyond a red bubble.
- `onText` receives the **full text so far** (`api.js:166`), which forces the O(n²) re-parse. A delta callback would allow append-only rendering.

### 2.5 UI placement — CONFIRMED

- Launcher: fixed `right:24px; bottom:24px` (`styles:835`), panel `right:24px; bottom:24px; width:min(440px,…); height:min(680px,…)` (`:838`).
- Mobile: full-screen panel (`:892`).
- There is **no** docked/permanent variant, no pin control, no resize. The user wants the overlay **kept** and a permanent right-hand panel **considered** — these are additive, not exclusive.

## 3. Every module the change would touch (file:line, each read)

**Frontend**
- `src/components/AssistantChat.jsx` — panel, renderer, send/stop/reset, quick actions. Largest change surface.
- `src/context/ChatContext.jsx` — chart store; needs to grow into a **page-context + action bus** (register page state, expose `navigate`, `setFilter`, `openDrawer`, `setTab`).
- `src/services/api.js` — `streamAssistantChat` (`:148-169`) needs delta streaming + an action/event channel; `AI_API_URL` (`:145`).
- `src/context/AppContext.jsx` — filters (`useFilters`) are the target of "apply a filter" actions.
- `src/components/Layout.jsx` — host for a docked panel variant and for the action dispatcher.
- `src/pages/*.jsx` — each page must publish a **page descriptor** (what tabs/drawers/filters it has) so the assistant can act on it. Product drawer state lives in `ProductAnalysis.jsx`; tab state in `AIRecommendations.jsx`.
- `src/styles/*.css` — `:835-895` assistant block; docked layout, cursor, code blocks, action chips.

**Backend**
- `backend/server.py` — `ChatRequest`/`/ai/chat`; add `actions`, `page.descriptor`, `conversationId`; possibly a new `/ai/action` result channel.
- `backend/assistant.py` — replace keyword intents with an **orchestrator** (tool selection + plan), add module prompts, add evidence collection.
- `backend/advisor.py` — `stream_chat` (`:314-383`) stays; add a non-streaming `chat` JSON mode call for the orchestrator's planning step (`chat(..., json_mode=True)` already exists at `:244`).
- `backend/services/analytics_service.py`, `recommendations.py`, `forecasting.py` — the Analytics/Marketing engines the orchestrator calls.
- `backend/api/analytics.py`, `marketing.py`, `products.py` — the Data Retrieval tools (already exist; the orchestrator should call the **service layer**, not HTTP).
- `backend/database/models.py` — `LLMCache` (`:122`) can cache expensive orchestrations; conversation persistence would need a new table **only if** Q8 says server-side.

**Tests**
- `backend/tests/` — no assistant coverage today; new tests for orchestrator routing, evidence grounding, "not enough data", action validation.
- `e2e/pages.spec.js` — add assistant flows (open, ask, stream, stop, new conversation, action chip).

## 4. The requirements, verbatim and mapped

### 4.1 The five modules (user's table, verbatim)

| Module | User's requirement | Exists today | Gap |
|---|---|---|---|
| **A. Marketing Strategy Generator** | "strategie completă de marketing pentru un anumit produs sau brand", with Market Research, Target Audience, Segmentation, Positioning, SWOT, Marketing Mix, Campaign Strategy, Budget Allocation, KPIs, Timeline, **and** "trebuie să explice de ce recomandă o anumită strategie și ce date susțin recomandarea" | one `campaign` intent prompt (`assistant.py:27-28`) | 9 of 10 components; no justification-with-data contract |
| **B. Chart Intelligence** | explain: what it shows, trend, max/min, anomalies, plausible causes, marketing implications, actions; answer "de ce a scăzut sentimentul", "care brand are cea mai bună percepție", "ce produs are cele mai multe recenzii negative", "cum se corelează prețul cu ratingul", "ce tendințe în ultimele 30 de zile"; **must receive the real data, not an image** | `chart_facts` + focused-chart raw data (`assistant.py:75-163`); real data already sent, not an image | cross-page/cross-chart queries; anomaly detection; correlation; time-range contract; chart ID + indicator in the request |
| **C. Consumer Intelligence** | preferences, segmentation, purchase drivers, recurring complaints, appreciated features, cross-category comparison; e.g. "de ce preferă Apple în detrimentul Samsung", grouped by ecosystem/design/performance/price/UX | segments passed as raw JSON (`advisor.py:221`); `sentiment` intent gives drivers | no review-derived clustering, no cross-brand preference extraction, no category grouping |
| **D. Competitor Intelligence** | positioning, price differences, consumer perception, competitive advantages, weaknesses from reviews, differentiation opportunities | `competitor` intent prompt (`assistant.py:33-35`) | no positioning map, no price-gap computation, no weakness extraction from reviews |
| **E. Campaign & Content Generator** | campaign ideas, ad messages, slogans, social content, editorial calendar, influencer proposals, launch campaigns, retention campaigns; structured objective/audience/message/channels/budget/calendar/KPI | `copy` and `calendar` intents (`:29-32`) | no ranked ideas, no influencer proposals, no retention, no structured block |

### 4.2 The six advanced features (verbatim names)

1. **Marketing Opportunity Detection** — from reviews, online interest, competitor differences. *Nothing exists.*
2. **Predictive Marketing Insights** — estimates only "dacă există suficiente date istorice", never presented as certainty. *`backend/services/forecasting.py` exists (UNVERIFIED: not read in this pass); no chat integration.*
3. **Automated SWOT Analysis** — for a brand or product, from collected data. *Nothing exists.*
4. **Customer Persona Generator** — from statistically identified segments. *Segments exist (`/api/analytics/consumer-segments`); no persona generation.*
5. **Marketing KPI Advisor** — CTR, Conversion Rate, CAC, ROAS, Engagement Rate, Customer Retention Rate per objective. *Nothing exists.*
6. **What-if Analysis** — e.g. "ce s-ar întâmpla dacă am reduce prețul cu 10%", using history or explicit assumptions, never claiming certainty. *Nothing exists.*

### 4.3 The architecture and technology the user proposed (verbatim)

Architecture components: **MarketPulse AI Assistant** (conversational UI) → **AI Orchestrator** (understands the question, selects tools) → **Analytics Engine** (statistics, charts, indicators) / **Marketing Engine** (strategies, campaigns, SWOT) / **Data Retrieval** (products, reviews, prices) / **Consumer Intelligence** (segments, preferences) → **Grounded AI Response** (explanations, recommendations, indicators, sources).

Technology table: AI Orchestrator = Python; API = FastAPI; LLM = OpenAI API or compatible; Data Analysis = Pandas, NumPy; ML = Scikit-learn; NLP = Transformers; Database = PostgreSQL; Context retrieval = SQL + eventual RAG; Frontend Chat = React.

**Repo reality check (CONFIRMED):** Python + FastAPI + React already match. The database is **MySQL**, not PostgreSQL (`backend/requirements.txt`: PyMySQL; `docker-compose.yml`; `/health` → `mysql+pymysql`). Pandas, NumPy and Scikit-learn were **deliberately removed** — `backend/requirements.txt` states: "pandas / numpy / scikit-learn were removed: nothing imports them"; `praw / textblob` likewise. Transformers is not installed. So the technology table is a **wish list**, not a constraint; see Q6.

### 4.4 Chart interpretation flow (user's spec)

Frontend sends: chart ID, indicator analysed, time range, actual data, applied filters. Backend forwards to the AI service, which may request additional computations, and returns the interpretation.

**Today:** `ChatRequest` (`server.py:116-122`) carries `charts[]` (each `{id,title,subtitle,data,note}`), `focusChart`, `page{path,title,filters}` and `brand`. It does **not** carry an explicit `indicator` or `range` field per chart, and there is no channel for the model to *request* more computation. The data is real (not an image) — that half of the requirement is already met.

### 4.5 UI repositioning (user's spec)

- Keep the floating "Ask AI" button + overlay — **explicitly requested** ("o vom păstra").
- Consider a permanent right-hand panel, top-to-bottom.
- The assistant should be able to "interacționa direct cu platforma și a o și controla: arată tab-uri, ajută, explică full, să poată controla tot".

**Today:** overlay only; no dock; no control of any kind.

### 4.6 Streaming (user's supplement)

"vom vrea să vedem output cu streaming în agent frumos formatat." Transport exists; render needs work (§2.4).

## 5. Recommendation (precise)

### 5.1 Architecture — the orchestrator, built from what exists

Do **not** throw away `assistant.py`. Wrap it:

```
POST /ai/chat
  └─ orchestrator.plan(message, page, charts, brand, history)
       ├─ step 0: deterministic intent+entity parse (extend assistant.detect_intent)
       ├─ step 1: tool selection (JSON mode, advisor.chat(json_mode=True))
       │     tools = [analytics.*, marketing.*, products.*, reviews.*, segments.*,
       │              competitor.*, forecast.*, strategy.*, swot.*, persona.*, kpi.*, whatif.*]
       ├─ step 2: execute the selected tools against the SERVICE layer (not HTTP)
       │     each returns {facts: [...], evidence: [{label, value, source, path}]}
       ├─ step 3: build the prompt from tool facts (never raw rows when facts exist)
       └─ step 4: stream the grounded answer + emit an `evidence` event
```

The orchestrator's planning call is **non-streaming** and cheap (small JSON); the answer call is the existing `advisor.stream_chat`. If planning fails or returns an unknown tool, fall back to today's behaviour — the chat must never become less reliable than it is now.

**Tools map to the user's engines:**

| User's component | Implementation |
|---|---|
| Analytics Engine | `backend/services/analytics_service.py` + `api/analytics.py` computations |
| Marketing Engine | new `backend/services/strategy.py` (strategy, SWOT, campaign, KPI advisor) |
| Data Retrieval | `backend/api/products.py`, `database/models.py` (Product, PriceHistory, Review) |
| Consumer Intelligence | new `backend/services/consumer.py` (segments, drivers, complaints) |
| Grounded AI Response | `assistant.build_messages` + an `evidence[]` list rendered as chips |

### 5.2 Module mapping — what each module becomes

**A. Strategy Generator** — a *template* prompt with the ten sections as a fixed skeleton, each section fed by pre-computed facts (market size/proxy, segment sizes, price position, sentiment drivers, competitor gaps). The "why" requirement is satisfied by an `evidence` list: every section cites `{metric, value, source}` and the renderer shows them as chips. If a section has no data, it prints **"Not enough data to support this section"** — never a fabricated number.

**B. Chart Intelligence** — extend `ChatRequest` with a per-chart `{indicator, range, series}` contract; add anomaly detection (z-score over the series) and correlation (price vs rating) as **tools**, not prompt instructions, because the model is unreliable at arithmetic. Cross-page queries work by letting the orchestrator call the analytics service directly instead of relying on mounted charts.

**C. Consumer Intelligence** — a tool that aggregates reviews by aspect and brand, returns ranked drivers/complaints with counts, and a prompt that must group by the user's categories (ecosystem, design, performance, price, UX). Cross-brand preference = driver delta between two brands, computed in Python.

**D. Competitor Intelligence** — tools: positioning (price vs sentiment/rating), price gaps vs median, review-derived weaknesses (negative-aspect frequency), differentiation opportunities (high-importance/low-satisfaction quadrant). The prompt turns tool output into the user's six bullets.

**E. Campaign & Content** — one tool per artefact (ideas, copy, slogans, calendar, influencer, launch, retention), each with a fixed output schema so the UI can render it consistently.

**Advanced features** — each is a tool + a template: opportunity detection (review gaps + interest delta + competitor gap), predictive (only when `len(history) >= N`, else "not enough history"), SWOT (strengths = top drivers, weaknesses = top complaints, opportunities = gaps, threats = competitor momentum), persona (from segment stats + drivers), KPI advisor (objective → KPI set, deterministic mapping), what-if (explicit assumption block + sensitivity from price history, labelled as an assumption).

### 5.3 UI — keep the overlay, add a dock, add actions

1. **Keep** the floating launcher + overlay exactly as is (user's explicit request).
2. **Add** a "pin to side" control in the header that switches the same component to a docked right column (`position: sticky`, full height, page content reflows). Same state, same messages — only layout changes. Default: overlay (no behaviour change for existing users).
3. **Formatted streaming**:
   - change `streamAssistantChat` to emit **deltas** (`onDelta`) in addition to the full text, so the renderer appends instead of re-parsing;
   - memoise completed blocks; only the last (in-progress) block re-renders;
   - add a blinking cursor while `pending`;
   - add fenced code blocks, links, blockquotes, `---`;
   - keep tables but buffer an unterminated table until its closing row (no layout snap);
   - add "Copy" on assistant messages.
4. **Platform control — declarative, never arbitrary.** The model never executes code. It emits a JSON `actions[]` block; the frontend validates each against a **whitelist of registered page capabilities** and renders them as **chips the user clicks**. Nothing happens without a click. Whitelist: `navigate(path)`, `set_filter({brand,source,range})`, `open_product(id)`, `set_tab(name)`, `focus_chart(id)`, `open_recommendation(id)`. No destructive action, no form submission, no external call. Unknown action → dropped and logged, never executed.
5. **Evidence chips** — each factual claim can carry `{label, value, source}`; the renderer shows them under the message, linking to the page/chart.

### 5.4 Delivery order (recommended)

**Slice 1 — "Chart Intelligence, properly" (highest value, smallest risk).**
Delta streaming + cursor + code/links + copy; chart `indicator`/`range` contract; anomaly + correlation tools; evidence chips; conversation persistence in `localStorage`; tests for `assistant.py` and the stream. *Why first:* it deepens the one module that already works and is the user's stated differentiator ("unul dintre cele mai interesante elemente diferențiatoare").

**Slice 2 — "Strategist".**
Orchestrator skeleton (planning + tool registry + fallback); Strategy Generator (10 sections + why/evidence); SWOT; KPI Advisor; Consumer and Competitor tools. *Why second:* these are prompt+tool work on top of Slice 1's evidence plumbing; no new UI paradigm.

**Slice 3 — "Control and simulation".**
Docked panel; declarative actions + chips; persona generator; opportunity detection; what-if; predictive (guarded by history length). *Why last:* actions need the page-capability registry from Slice 1–2, and what-if needs the price history tools.

Each slice ends with the full gate (pytest, Playwright, build) and a Camoufox proof of the new behaviour.

## 6. Risks

1. **Model quality.** The free model is weak at arithmetic and long structured output. Mitigation: pre-compute every number in Python (already the pattern in `chart_facts`); the model only narrates. A stronger model is Q4.
2. **Latency.** Planning + tools + streaming can exceed 30 s. Mitigation: tools are local SQL/Python (fast); planning is a small JSON call; stream the answer as soon as the first tool returns. Never block the UI.
3. **Prompt injection via data.** Reviews are user-generated text and flow into the prompt. Mitigation: keep data in a clearly delimited block, instruct the model that data is data, never instructions; the action whitelist means injected text cannot cause a side effect.
4. **Action safety.** A model choosing the wrong action. Mitigation: chips require a click; whitelist; no destructive verbs; the action is a *suggestion*, not an execution.
5. **Cost.** Every question is at least one LLM call, often two (plan + answer). Mitigation: cache orchestrations in `LLMCache` (`models.py:122`); reuse `advisor`'s existing 600 s recommendation cache pattern.
6. **Scope creep.** The user listed five modules and six features; shipping all at once breaks "one concern per PR". Mitigation: the three slices above; each is a separate PR.
7. **Breaking the current chat.** The orchestrator must fall back to today's keyword path on any failure. A regression here is worse than a missing feature.
8. **Docked layout.** Reflowing page content can break charts (`ResponsiveContainer` needs a resize). Mitigation: dock as an overlay column that shrinks the main area with a CSS transition, and let `ResponsiveContainer` re-measure; verify on all eight pages.
9. **Persistence and privacy.** Conversations may contain business data. `localStorage` is per-browser; no server storage until auth exists (Q8).
10. **Test debt.** Zero assistant tests today; every slice must add them or the gate will not protect the new code.

## 7. QUESTIONS for the user (numbered, a recommendation each; "all rec" answers them)

**Q1 — Module priority.** Which module ships first? The five are A Strategy, B Chart Intelligence, C Consumer, D Competitor, E Campaign/Content.
**Recommendation:** **B first** (deepen what already works — it is the stated differentiator and needs no new UI), then **A** (the strategist identity), then **E**, then **C** and **D** together (both are review-analysis tools sharing one aggregator).

**Q2 — Panel placement.** Keep the floating overlay only, switch to a permanent right-hand dock, or both with a pin toggle?
**Recommendation:** **both, overlay by default**, with a "pin to side" control in the header. This honours "o vom păstra" literally, adds the permanent panel the user asked to consider, and changes nothing for anyone who does not click pin.

**Q3 — How much platform control.** (a) Read-only explanations; (b) suggest actions as chips the user clicks; (c) execute actions directly when the model decides.
**Recommendation:** **(b)** — declarative, whitelisted actions rendered as chips, executed only on a user click. (c) is unsafe: a wrong navigation or filter silently changes what the user is looking at, and injected review text could trigger it.

**Q4 — Model and reasoning latency.** Stay on the free `dots-studio/dots-3-note-preview:free`, or add a stronger model for planning/strategy with a longer timeout?
**Recommendation:** **keep the free model as the default and add a per-request "Deep reasoning" toggle** that switches to a stronger model for the planning step and strategy/SWOT answers. Show an estimated wait; never block the UI; fall back to the free model on error or timeout.

**Q5 — Behaviour when data is missing.** Show "0", hide the section, or say "not enough data"?
**Recommendation:** **say "Not enough data" and name what is missing and what would unlock it** (e.g. "needs ≥ 8 weeks of price history; you have 4"). Never 0, never a fabricated number — this matches the repo rule "no placeholder presented as product".

**Q6 — New libraries.** The user's technology table lists Pandas, NumPy, Scikit-learn, Transformers. All were deliberately removed (`backend/requirements.txt`), and the DB is MySQL, not PostgreSQL.
**Recommendation:** **add none of them for now.** Compute aggregates in SQL and Python's stdlib (the existing `chart_facts` pattern); add a library only if a specific feature cannot be done otherwise, and then one at a time with a measured justification. Keep MySQL.

**Q7 — Streaming fidelity.** Is the current token stream enough, or is a richer render required?
**Recommendation:** **richer render** — delta-based append rendering, typing cursor, fenced code, links, blockquotes, buffered tables, copy button. This is what "frumos formatat" means in practice; the transport already streams, so the work is in `AssistantChat.jsx` only.

**Q8 — Conversation persistence.** React state only, `localStorage`, or server-side history?
**Recommendation:** **`localStorage`**, capped (e.g. last 20 messages per conversation, last 10 conversations), with "New conversation" clearing it. Server-side history needs auth and a schema change; defer until there is a user model.

**Q9 — Evidence / citations.** Must every factual claim cite its data source?
**Recommendation:** **yes, for every number the assistant states** — an `evidence[]` list rendered as chips (`{label, value, source}`), produced by the tools, not by the model. This is the mechanism that makes "grounded" verifiable rather than a promise.

**Q10 — First release scope.** Ship the whole vision, or slice it?
**Recommendation:** **three slices as in §5.4** — (1) Chart Intelligence + streaming + persistence + evidence; (2) orchestrator + Strategy + SWOT + KPI Advisor + Consumer/Competitor; (3) dock + actions + persona + opportunity + what-if + predictive. Each slice is one PR, gated and proven.

## 8. CONFIRMED / UNVERIFIED / NOT DONE

**CONFIRMED (read the exact line or ran it):**
- The chat, streaming transport, intent table, chart facts, context builder, recommendation engine and DB tables exist at the `file:line` cited in §2.1–§2.2.
- No assistant tests: `grep -rn "assistant\|/ai/chat" backend/tests/*.py` → zero matches.
- Current model is `dots-studio/dots-3-note-preview:free` (`GET 127.0.0.1:8020/health`).
- Pandas/NumPy/Scikit-learn are absent by explicit decision (`backend/requirements.txt` comment).
- The Markdown renderer cannot render code fences, links, blockquotes or `---` (`AssistantChat.jsx:25-70`).
- `onText` receives the full accumulated text (`api.js:166`), which forces the O(n²) re-render.
- `POST /ai/advice` has no caller in `src/` (grep over `src/`).

**UNVERIFIED (inferred, not executed):**
- `backend/services/forecasting.py` capabilities (not read in this pass).
- Whether any page exposes tab/drawer state in a form an action bus could drive without refactoring (read only `ProductAnalysis.jsx` and `AIRecommendations.jsx` at a high level).
- Real latency of a planning + answer round trip on the free model.
- Whether the free model can reliably emit the orchestrator's JSON plan (small models often cannot; this is the main technical risk of Slice 2).

**NOT DONE (and why):**
- No code written; this is a read-only spec.
- No live LLM call made (would consume the user's quota without consent).
- No measurement of token cost per module.
- No prototype of the action-chip mechanism.

## 9. Left on disk

Nothing. No files created outside this spec; no processes started; no database writes. The working tree carries only the pre-existing `node_modules/.vite` churn from the running dev server (untracked/gitignored) and this new spec file.

## USER DECISIONS (<pending>, binding)

_Appended by the orchestrator only, after the user answers §7._
