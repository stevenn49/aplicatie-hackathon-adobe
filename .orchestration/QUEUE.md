# QUEUE.md — the PR queue (binding order since 2026-11-07)

**Rule:** this file is updated at every PR start and every PR end, in full detail. Statuses: **RUNNING** · **QUEUED** · **FINISHED** (plus SPEC FIRST / NEEDS GO / HELD as sub-notes). One production PR at a time; read-only investigators may run beside it, never more than 2 agents total. Every PR: draft at code freeze → gate green on the final commit → squash-merge → verified by the orchestrator (WORKING-NOTES II.5) → row flipped to FINISHED here.
Spec paths are under `.orchestration/specs/`. "User decisions" names the binding block inside that spec (the user's answers, with time). When rows are merged (the user may group same-file, same-proof items into one PR), the merged row carries each absorbed item's original cells verbatim under its label and keeps the old item numbers in brackets so the specs still line up; frozen-file, data-rewriting, spec-first and feature items stay alone.

---

## RUNNING

**2026-11-07 — integration arc, uncommitted.** Items 1-4 and 6-7 are implemented and verified locally. Nothing committed yet; the user asked for a commit and push of the code plus the tracking files. No agent dispatched — the orchestrator did the work directly because the contract had to be designed as one piece.

_(no production PR running)_

---

## QUEUED (in order)

| # | Item | Version / note | Spec + user decisions | What it does and why |
|---|---|---|---|---|
| 5 | **OpenRouter LLM service** | 1.5.0 MINOR, T2 | `002-llm-openrouter.md` (to write) + USER DECISIONS pending | The service, the cache and the three call sites are built and degrade honestly. **Blocked on the user's API key and free model id** — until then every LLM surface reports `"source": "derived"`. |

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

**Investigations finished (no release):** `001-audit-and-integration.md` — the full audit; all nine questions answered.

---

## HELD — waits until the user says go
- **Push to `origin/main`** — the user asked for a commit and push; the push happens in this turn.
- **Removing `node_modules/` from git history** — 89.8 MB committed; destructive, needs its own go.
- **OpenRouter key and model id** — the user supplies both.
