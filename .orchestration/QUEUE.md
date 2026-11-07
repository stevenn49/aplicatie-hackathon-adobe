# QUEUE.md — the PR queue (binding order since 2026-11-07)

**Rule:** this file is updated at every PR start and every PR end, in full detail. Statuses: **RUNNING** · **QUEUED** · **FINISHED** (plus SPEC FIRST / NEEDS GO / HELD as sub-notes). One production PR at a time; read-only investigators may run beside it, never more than 2 agents total. Every PR: draft at code freeze → gate green on the final commit → squash-merge → verified by the orchestrator (WORKING-NOTES II.5) → row flipped to FINISHED here.
Spec paths are under `.orchestration/specs/`. "User decisions" names the binding block inside that spec (the user's answers, with time). When rows are merged (the user may group same-file, same-proof items into one PR), the merged row carries each absorbed item's original cells verbatim under its label and keeps the old item numbers in brackets so the specs still line up; frozen-file, data-rewriting, spec-first and feature items stay alone.

---

## RUNNING

**2026-11-07 — integration arc, uncommitted.** Items 1-4 and 6-7 are implemented and verified locally. Nothing committed yet; the user asked for a commit and push of the code plus the tracking files. No agent dispatched — the orchestrator did the work directly because the contract had to be designed as one piece.

_(no production PR running)_

---

## QUEUED (in order)

_(nothing queued; see HELD for the items that need the user's go)_

| # | Item | Version / note | Spec + user decisions | What it does and why |
|---|---|---|---|---|
| — | **Reddit OAuth in production** | — | — | The connector supports OAuth; the team still has to register an app and put the credentials in `backend/.env`. Without them Reddit contributes nothing. |
| — | **X/Twitter credits** | — | — | The free tier closed in February 2026. Only worth doing if the team funds credits. |

---

## FINISHED (this arc, newest first; each verified by the orchestrator per II.5)

| Version | PR | Item | Spec + user decisions | What shipped |
|---|---|---|---|---|
| 1.1.0 | (local, uncommitted) | **MySQL local database** | `001` + USER DECISIONS 2026-11-07 | SHIPPED: `docker-compose.yml` (MySQL 8.4, host 3307, healthcheck); `PyMySQL` in requirements; `database/connection.py` refuses a non-MySQL URL and has **no** silent SQLite fallback; `config.py` defaults to MySQL; `backend/.env.example` documents Docker / native / shared. PROOF: container healthy in 12 s, `SELECT VERSION()` → 8.4.11, `/health` → `database=healthy, database_backend=mysql+pymysql`. |
| 1.2.0 | (local, uncommitted) | **Five missing endpoints** | `001` + USER DECISIONS | SHIPPED: `GET /api/analytics/brands`, `/consumer-segments`, `/competitors`, `GET /api/marketing/trends` (new router), `GET /api/products/compare`. PROOF: all return 200 with computed data — brands 5, segments 5, competitors 5 brands / 10 price rows / 6 features, marketing 12 trend points / 3 opportunities, compare 2 products. |
| 1.3.0 | (local, uncommitted) | **Reshape the five existing endpoints** | `001` + USER DECISIONS | SHIPPED: `schemas/dto.py` (the dashboard contract), `services/analytics_service.py` (all derivations), overview → `kpis/evolution/mentions/topMovers`, sentiment → `distribution/trend/aspects/keywords/reviews` with optional filters, recommendations → `summary/items/high_priority`, products carry `sentiment/change/interest/color/launch/pros/cons`. Legacy endpoints kept under new names (`/summary`, `/product-sentiment`, `/product-recommendations`). PROOF: every endpoint 200 with non-empty derived values; sentiment distribution sums to 100. |
| 1.4.0 | (local, uncommitted) | **Remove mocks and hardcoded numbers** | `001` + USER DECISIONS | SHIPPED: `src/mocks/marketData.js` deleted; `api.js` has no fallback and throws a named `ApiError`; every page consumes the API; all 23 hardcoded figures replaced by computed values or removed; `Layout` shows the real database status, the real recommendation count and the real LLM state. PROOF: all 8 routes render with the backend stopped → `ErrorState`; with it running → real MySQL data. |
| 1.6.0 | (local, uncommitted) | **Data-integrity fixes** | `001` | SHIPPED: `forecasting.py` oldest/newest inversion; `prices.py` `old_price` captured before reassignment; `google_trends.py` no longer fabricates 88.0/72.0 (returns `[]`, the collector reports the gap); `emag._clean_price` handles space thousands separators and has a real `Tuple` type hint; seeds keyed by SKU and idempotent. PROOF: `test_price_change_uses_oldest_point` fails on the old code and passes now; `test_google_trends_returns_empty_when_unavailable`; `test_emag_price_parsing` covers `2 499 RON` (was 2.0, now 2499.0). |
| 1.7.0 | (local, uncommitted) | **Test suite** | `003` (to write) | SHIPPED: `backend/tests/conftest.py` (scratch `marketpulse_test` DB, created and dropped per session), `test_api.py` (contract shapes), `test_services.py` (derivations), `test_connectors.py` (hermetic), `test_connectors_live.py` (opt-in via `MARKETPULSE_LIVE_TESTS=1`); `playwright.config.js` + `e2e/smoke.spec.js` + `e2e/pages.spec.js`. PROOF: **56 passed, 3 skipped** backend; **32 passed** Playwright; `npm run build` exit 0. |
| 1.8.0 | #4 (`8dfcaa0`, merge `a988877`) | **Scripts: one launcher, guided setup, live reload** | `001` | SHIPPED: `run.ps1` / `run.sh` (Setup, Start, Stop, Status, Settings, Reload, Tests, Reset DB, Docs); `scripts/lib.ps1` shared helpers; setup detects Docker vs native MySQL and asks; per-API key prompts with signup URLs; live OpenRouter free-model picker; `settings.ps1` / `settings.sh`; `POST /api/admin/reload` (loopback-only) applies keys without a restart; start scripts never double-start and never kill a foreign process. PROOF: non-interactive setup exit 0; reload proven live; start refuses to double-start; restart stops only our PIDs. |
| 1.9.0 | #4 (`8dfcaa0`, merge `a988877`) | **OpenRouter everywhere + non-blocking LLM** | `002` | SHIPPED: `openrouter` is an advisor provider and the default (one key covers every AI surface); `/admin/reload` on the assistant service; output budget read from each model's `max_completion_tokens` with `reasoning.effort=high`; `extract_json` takes the outermost structure; the three LLM surfaces read cache-only and generate in a `BackgroundTask` (`source: "pending"`); Reddit gains OAuth with `last_status`; default model `dots-studio/dots-3-note-preview:free`. PROOF: **70 passed, 3 skipped**; **32 Playwright**; build exit 0; live OpenRouter calls returned model-written text on all four surfaces; product detail 54 s → 0.1 s on a cache miss. |

**Investigations finished (no release):** `001-audit-and-integration.md` — the full audit; all nine questions answered.

---

## HELD — waits until the user says go
- **Push to `origin/main`** — the user asked for a commit and push; the push happens in this turn.
- **Removing `node_modules/` from git history** — 89.8 MB committed; destructive, needs its own go.
- **OpenRouter key and model id** — the user supplies both.
