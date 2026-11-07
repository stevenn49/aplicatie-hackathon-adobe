# QUEUE.md — the PR queue (binding order since 2026-11-07)

**Rule:** this file is updated at every PR start and every PR end, in full detail. Statuses: **RUNNING** · **QUEUED** · **FINISHED** (plus SPEC FIRST / NEEDS GO / HELD as sub-notes). One production PR at a time; read-only investigators may run beside it, never more than 3 agents total. Every PR: draft at code freeze → gate green on the final commit → squash-merge → verified by the orchestrator (WORKING-NOTES II.5) → row flipped to FINISHED here.

Spec paths are under `.orchestration/specs/`. "User decisions" names the binding block inside that spec (the user's answers, with time). When rows are merged (the user may group same-file, same-proof items into one PR), the merged row carries each absorbed item's original cells verbatim under its label and keeps the old item numbers in brackets so the specs still line up; frozen-file, data-rewriting, spec-first and feature items stay alone.

---

## RUNNING

**2026-11-07 17:45 — three Opus agents in flight, deadline 19:30.**

| Agent | Branch / output | Scope | State |
| --- | --- | --- | --- |
| **E2E fixer** | `fix/e2e-findings` | Tests every page in Camoufox and repairs what is broken. Must keep the gate green. | running |
| **Spec 004** | `.orchestration/specs/004-ai-strategist-chatbot.md` | Read-only investigation of the AI Marketing Strategist expansion | running |
| **Spec 005** | `.orchestration/specs/005-intelligence-modules.md` | Read-only investigation of the 10 intelligence modules | running |

What the user owes: nothing right now. What is next: read the three reports, verify the claims, flip the rows.

---

## QUEUED (in order)

| # | Item | Version / note | Spec + user decisions | What it does and why |
|---|---|---|---|---|
| 1 | **AI Marketing Strategist chatbot** | MINOR, T2 | `004-ai-strategist-chatbot.md` + USER DECISIONS pending | Turns the assistant into a consultant: Marketing Strategy Generator, Chart Intelligence, Consumer Intelligence, Competitor Intelligence, Campaign & Content Generator, plus six advanced features (Opportunity Detection, Predictive Insights, Automated SWOT, Persona Generator, KPI Advisor, What-if). Repositioned UI, streaming output. Questions from the agent must be answered first. |
| 2 | **Intelligence modules** | MINOR, T2 | `005-intelligence-modules.md` + USER DECISIONS pending | Ten modules: Product Radar, Review Mining (ABSA), Competitor Benchmarking, Trend Discovery, Marketing Campaign Lab, Customer Segmentation (ML), Price Intelligence (anomaly detection), Brand Health Monitor, Market Opportunity Finder, Automated Business Reports (PDF/Excel/CSV/PPTX). Plus eight smaller features and full product CRUD in the UI. |
| 3 | **Product CRUD in the UI** | MINOR, T1 | folded into `005` | The backend already has POST / PUT / DELETE and `import-from-emag`; the frontend has no way to use them. Add, edit, delete and import products from Product Analysis. |
| 4 | **Reddit OAuth in production** | — | — | The connector supports OAuth; the team still has to register an app and put the credentials in `backend/.env`. Without them Reddit contributes nothing. |
| 5 | **X/Twitter credits** | — | — | The free tier closed in February 2026. Only worth doing if the team funds credits. |

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

**Investigations finished (no release):** `001-audit-and-integration.md` — the full audit, all nine questions answered.

---

## HELD — waits until the user says go

- **Push of the E2E fixer's branch** — it commits to `fix/e2e-findings` and does not push. Merging needs the gate re-run and the user's go.
- **Removing `node_modules/` from git history** — 89.8 MB committed; destructive, needs its own go.
- **Ollama / Groq / Gemini** — implemented, never exercised against a real provider.
- **Reddit OAuth** and **X credits** — see QUEUED items 4 and 5.
