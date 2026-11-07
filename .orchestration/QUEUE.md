# QUEUE.md — the PR queue (binding order since 2026-11-07)

**Rule:** this file is updated at every PR start and every PR end, in full detail. Statuses: **RUNNING** · **QUEUED** · **FINISHED** (plus SPEC FIRST / NEEDS GO / HELD as sub-notes). One production PR at a time; read-only investigators may run beside it, never more than 3 agents total. Every PR: draft at code freeze → gate green on the final commit → squash-merge → verified by the orchestrator (WORKING-NOTES II.5) → row flipped to FINISHED here.

Spec paths are under `.orchestration/specs/`. "User decisions" names the binding block inside that spec (the user's answers, with time). When rows are merged (the user may group same-file, same-proof items into one PR), the merged row carries each absorbed item's original cells verbatim under its label and keeps the old item numbers in brackets so the specs still line up; frozen-file, data-rewriting, spec-first and feature items stay alone.

---

## RUNNING

**Nothing is running. 2026-11-07 18:42 — PR #5 merged, `main` is `edf610f`, the checkout is in sync (`0 0`).**

All three agents finished. The E2E fixer delivered and its work is merged. Both investigations are written and decided.

---

## QUEUED (in order)

**The user answered `all rec` at 2026-11-07 17:51.** Both specs carry a binding `USER DECISIONS` block. The order below follows those decisions. **Item 1 shipped in #5 (1.10.0) and has been removed from this table.**

| # | Item | Version / note | Spec + user decisions | What it does and why |
|---|---|---|---|---|
| 2 | **Review Mining / ABSA** | MINOR, T2 | `005` + USER DECISIONS (Q1) | The aspect table already exists (`sentiment_analysis.py:44-122`, `analytics_service.py:141-167`). Add the reasons extracted from review text and exact mention counts. Zero new data needed. |
| 2 | **Review Mining / ABSA** | MINOR, T2 | `005` + USER DECISIONS (Q1) | The aspect table already exists (`sentiment_analysis.py:44-122`, `analytics_service.py:141-167`). Add the reasons extracted from review text and exact mention counts. Zero new data needed. |
| 3 | **Brand Health Monitor** | MINOR, T2 | `005` + USER DECISIONS (Q1) | Sentiment, SOV, mentions, themes, competitor comparison. Missing: per-brand sentiment trend and the explicit "only the sources we monitor" warning. |
| 4 | **Price Intelligence** | MINOR, T2 | `005` + USER DECISIONS (Q1, Q7) | History, fluctuations, percentage differences, price vs rating. Rule-based anomaly detection only (4 points per product, one retailer). Add the `retailer` column now, populate eMAG only, label "1 retailer monitored". |
| 5 | **Competitor Benchmarking** | MINOR, T2 | `005` + USER DECISIONS (Q1) | Sentiment, ratings, price positioning, price-vs-perception map, feature matrix. Missing: innovation indicators and real popularity. |
| 6 | **Chart Intelligence v2** | MINOR, T2 | `004` + USER DECISIONS (Q1, Q3, Q5, Q7) | The stated differentiator and the first slice of the assistant work: anomalies, correlations, "why did it drop", the last 30 days (the `range` filter is not wired to any API). Plus the richer streaming render: delta append, typing cursor, code blocks, links, buffered tables, copy button. |
| 7 | **Marketing Strategy Generator** | MINOR, T2 | `004` + USER DECISIONS (Q1, Q4) | The ten components: Market Research, Target Audience, Segmentation, Positioning, SWOT, Marketing Mix, Campaign Strategy, Budget Allocation, KPIs, Timeline — plus "why this strategy and which data supports it". |
| 8 | **Campaign & Content Generator** | MINOR, T2 | `004` + USER DECISIONS (Q1) | Campaign ideas ranked, ad copy, slogans, social content, editorial calendar, influencer proposals, launch and retention campaigns. |
| 9 | **Consumer + Competitor Intelligence in the assistant** | MINOR, T2 | `004` + USER DECISIONS (Q1) | Both share one review-analysis aggregator: preference extraction, complaint clustering, "why Apple over Samsung", positioning map, price-gap analysis, differentiation opportunities. |
| 10 | **Assistant orchestrator + tool registry** | MINOR, T3 | `004` + USER DECISIONS (Q3, Q4, Q8) | Phase 0 of the assistant work: replace the keyword table (`assistant.py:53-60`) with tool selection, add the declarative action chips (whitelisted, executed only on a user click), the "Deep reasoning" toggle, and conversation persistence. |
| 11 | **Automated Business Reports** | MINOR, T2 | `005` + USER DECISIONS (Q3, Q10) | Assemble the existing services into a report. CSV + Excel first, then PDF + PowerPoint. On demand only; no scheduler. |
| 12 | **Product Radar + composite scores** | MINOR, T2 | `005` + USER DECISIONS (Q1, Q8) | Product Competitiveness Score, Trend Momentum (append-only history; the search component stays `null` until there are 2 points), Market Opportunity Score. |
| 13 | **Customer Segmentation (ML) + Campaign Lab** | MINOR, T3 | `005` + USER DECISIONS (Q5, Q6, Q9) | Review-level audience segments with a silhouette quality score and an "exploratory, n=48" label. Campaign Lab as a scenario calculator with visible formulas, labelled "scenario, not prediction". |
| 14 | **Reddit OAuth in production** | — | — | The connector supports OAuth; the team still has to register an app and put the credentials in `backend/.env`. Without them Reddit contributes nothing. |
| 15 | **X/Twitter credits** | — | — | The free tier closed in February 2026. Only worth doing if the team funds credits. |

---

## FINISHED (this arc, newest first; each verified by the orchestrator per II.5)

| Version | PR | Item | Spec + user decisions | What shipped |
|---|---|---|---|---|
| 1.1.0 | local | **MySQL local database** | `001` + USER DECISIONS 2026-11-07 | `docker-compose.yml` (MySQL 8.4, host 3307, healthcheck); PyMySQL; `connection.py` refuses a non-MySQL URL and has **no** silent SQLite fallback. PROOF: container healthy in 12 s, `SELECT VERSION()` → 8.4.11, `/health` → `database=healthy`. |
| 1.2.0 | local | **Five missing endpoints** | `001` | `/api/analytics/brands`, `/consumer-segments`, `/competitors`, `/api/marketing/trends`, `/api/products/compare`. PROOF: all 200 with computed data. |
| 1.3.0 | local | **Reshape the five existing endpoints** | `001` | `schemas/dto.py`, `services/analytics_service.py`; overview → kpis/evolution/mentions/topMovers; sentiment → distribution/trend/aspects/keywords/reviews; recommendations → summary/items. Legacy contracts kept under new paths. PROOF: every endpoint 200, distribution sums to 100. |
| 1.4.0 | local | **Remove mocks and hardcoded numbers** | `001` | `src/mocks/` deleted; `api.js` has no fallback; all 23 hardcoded figures replaced; `Layout` shows real status. PROOF: 8 routes render real MySQL data, zero error states. |
| 1.6.0 | local | **Data-integrity fixes** | `001` | `forecasting.py` oldest/newest inversion; `prices.py` old_price; `google_trends.py` no fabricated score; `emag._clean_price` space separators; seeds keyed by SKU. PROOF: regression tests that fail on the old code. |
| 1.7.0 | local | **Test suite** | `003` | `conftest.py` (scratch `marketpulse_test` DB), `test_api.py`, `test_services.py`, `test_connectors.py`, `test_connectors_live.py` (opt-in); `playwright.config.js`, `e2e/smoke.spec.js`, `e2e/pages.spec.js`. PROOF: 56 pytest, 32 Playwright, build exit 0. |
| 1.8.0 | `c9516af` | **Scripts: launcher, guided setup, live reload** | `001` | `run.ps1`/`run.sh` (9 options); `scripts/lib.ps1`; setup detects Docker vs native MySQL and asks; per-API key prompts; live OpenRouter free-model picker; `settings.ps1`/`settings.sh`; `POST /api/admin/reload` (loopback-only); start never double-starts and never kills a foreign process. PROOF: non-interactive setup exit 0; reload proven live; start refuses to double-start. |
| 1.9.0 | **#4** `8dfcaa0` → `a988877` | **OpenRouter everywhere + non-blocking LLM** | `002` | `openrouter` is an advisor provider and the default; `/admin/reload` on the assistant; output budget from each model's `max_completion_tokens` with `reasoning.effort=high`; `extract_json` takes the outermost structure; the three LLM surfaces read cache-only and generate in a `BackgroundTask`; Reddit OAuth with `last_status`; default model `dots-studio/dots-3-note-preview:free`. PROOF: 70 pytest, 32 Playwright, build exit 0; live calls on all four surfaces; drawer 54 s → 0.1 s. |
| 1.9.1 | `764bd88` | **Assistant grounded in live MySQL** | `002` | `load_market_data()` builds the context from the running API (`/analytics/overview`, `/brands`, `/products`, `/consumer-segments`, `/sentiment`, `/competitors`) and caches it 2 minutes; `market_data.json` only as a fallback, marked `source: "snapshot"`. **Why:** the assistant answered "Samsung 79, average 82.6" from the stale snapshot; MySQL says 82.9 and 76.1. PROOF: `load_market_data(force=True)` → `source=live`; live chat now answers 82.9 / 76.1. |

| 1.9.2 | `c3d3894` | **Three defects the spec investigation found** | `004` | `advisor.py:451` read `data["exampleRecommendations"][0]`, a key that exists only in the bundled snapshot; once the assistant moved to live data the endpoint raised KeyError and returned **500**. `scripts/start.ps1` and `start.sh` started `main:app` and Vite but **not** `backend/server.py`, so a clean `run.ps1` produced a dashboard whose Ask AI panel was dead. `specs/README.md` listed two specs that were never written. PROOF: endpoint 500 → 5 items; both launchers now read `VITE_AI_API_URL`, start the assistant, wait for `/health`, and stop it on exit; gate 70 pytest / build exit 0. |
| 1.10.0 | **#5** `edf610f` | **[1] Product CRUD in the UI + the E2E sweep** | `005` + USER DECISIONS 17:51 (Q1, Q4) | `request()` gained `method`/`body` (byte-identical when unset; a 204 still returns `null` without reading JSON); added `createProduct`, `updateProduct`, `deleteProduct`, `importProductFromEmag`; `ProductAnalysis.jsx` gained an Add-product drawer with validation, an Import-from-eMAG bar that shows the 503 detail verbatim, and Edit/Delete in the product drawer behind a confirmation. Six defects fixed with it: `launch` missing from `ProductBase`/`ProductUpdate`; duplicate SKU **500 → 409**; **eMAG import 500 for any title over 150 chars** (`ProductResponse` re-applied the input length rule at serialisation, after the INSERT had committed — hence the duplicate rows); 11 charts invisible to the assistant and missing their "Analyse" button; Consumer Insights calling a sentiment score "Influence score"; `advisor.py:451` KeyError on live data; both launchers leaving the assistant dead. Both version strings were stale (1.0.0 / 1.1.0) and are now **1.10.0**. PROOF: CRUD exercised live on 8010 — 201 with `launch`, 409 on the duplicate, 200 on update, 204 on delete, catalogue back to 10; one live eMAG import 201 (a real 6,299.99 RON MacBook Air) then deleted; gate **70 pytest / 32 Playwright / build exit 0**, run by the orchestrator on the final commit. |

**Investigations finished (no release):** `001-audit-and-integration.md` — the full audit, all nine questions answered. `004-ai-strategist-chatbot.md` and `005-intelligence-modules.md` — both written by read-only Opus investigators, both carry a binding `USER DECISIONS` block from 2026-11-07 17:51 (`all rec`).

---

## HELD — waits until the user says go

- **Removing `node_modules/` from git history** — 89.8 MB committed; destructive, needs its own go.
- **Ollama / Groq / Gemini** — implemented, never exercised against a real provider.
- **Reddit OAuth** and **X credits** — see QUEUED items 14 and 15.

## KNOWN DEFECTS FOUND BUT NOT FIXED (from the E2E fixer's report, 18:35 — re-verify before citing)

| # | Defect | Evidence | Where it would be fixed |
|---|---|---|---|
| D1 | **"Stop generating" in the assistant does not stop generation.** | Instrumented: the DOM click reaches the button, but `AbortController.prototype.abort` is never called (`window.__aborts === 0`). The agent could not separate this from a tab that had already crashed with `out of memory`, so the cause is unconfirmed. | Needs a reproduction on a fresh page first. |
| D2 | **`out of memory` in the console after long assistant answers.** | Suspected O(n²): `AssistantChat.jsx:34-70` re-parses the whole accumulated text on every chunk. Not confirmed. | Same slice as D1. |
| D3 | **`POST /ai/advice` has no caller anywhere in `src/`.** | Dead code. | Delete or wire it — a decision, not a fix. |
| D4 | **Untested surfaces:** dark/light theme by hand, responsive at 375×812, the brand selectors on Brand Intelligence. | The Playwright suite covers the theme toggle, the global filters and all routes (32 green), but not these by hand. | The next E2E pass. |
