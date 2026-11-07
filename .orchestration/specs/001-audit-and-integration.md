# INVESTIGATION — Full audit and integration plan (2026-11-07, read-only, Opus 5)

Written by the orchestrator. No commits, no edits outside `.orchestration/`, no live calls beyond zero. CONFIRMED = ran it or read the exact line, output shown; UNVERIFIED = inferred; NOT DONE = skipped, and why.

## 0. Answer in five lines

The app is **100 % mock-driven**: `src/services/api.js` returns fixtures from `src/mocks/marketData.js` whenever `VITE_API_URL` is unset, and several pages import mocks directly regardless. The backend exists and is coherent, but the frontend requests **ten endpoints; five exist; none match in shape** — so setting `VITE_API_URL` (which the root `.env.example` tells you to do) breaks every page. MySQL is not supported (only SQLite and PostgreSQL drivers), and there is no LLM anywhere despite the product being sold as AI. The fix is a contract-first integration: backend serves the shapes the pages consume, frontend stops importing mocks, every number in the UI comes from stored data. Nothing here is a mystery — it is a large but mechanical build.

## 1. The problem as reported and the reproduction

The user's words: *"assess full qa, functionality, add db ... properly test and check and asses all full features see of the backend and frontend are fully connected and make sure the app is 100% real and functional with no placeholders or other issues."*

Reproduction of the core defect, by reading:

1. `src/services/api.js:3` — `const API_URL = import.meta.env.VITE_API_URL || "";`
2. `src/services/api.js:17` — `if (!API_URL) return delay(fallback);`
3. Root `.env.example:1` — `VITE_API_URL=http://localhost:8000`

Following the repo's own README ("copy `.env.example` to `.env.local`") therefore points the frontend at a backend whose paths and shapes do not match. Every page would render `ErrorState`.

With no `.env.local`, the app renders perfectly and shows entirely fabricated data.

## 2. Measured findings

### 2.1 Endpoint contract: requested vs served

| # | Frontend requests (`src/services/api.js`) | Backend serves | Status |
|---|---|---|---|
| 1 | `GET /analytics/overview` | `GET /api/analytics/overview` | path mismatch + shape mismatch |
| 2 | `GET /products` | `GET /api/products/` | path mismatch + shape mismatch |
| 3 | `GET /products/compare?ids=` | — | **missing** |
| 4 | `GET /products/{id}` | `GET /api/products/{id}` | path + shape mismatch |
| 5 | `GET /analytics/brands` | — | **missing** |
| 6 | `GET /analytics/sentiment` | `GET /api/analytics/sentiment?product_id=` | path + required param + shape |
| 7 | `GET /analytics/consumer-segments` | — | **missing** |
| 8 | `GET /marketing/trends` | — | **missing** (no marketing router at all) |
| 9 | `GET /analytics/competitors` | — | **missing** |
| 10 | `GET /analytics/recommendations` | `GET /api/analytics/recommendations` | path + shape mismatch |

CONFIRMED by reading `src/services/api.js:23-49` and `backend/api/products.py:24-25`, `backend/api/analytics.py:23-26`, `backend/main.py:60-61`.

### 2.2 Shape mismatches (what the pages actually consume)

- `getMarketOverview` → `{kpis:[{label,value,suffix,change,note,tone,icon,spark}], evolution:[{month,Apple,NVIDIA,Microsoft,Samsung,Sony}], mentions:[{id,brand,initials,text,source,time,sentiment,engagement}], topMovers:[{id,name,brand,category,change,color}]}`. Backend returns `{total_products, average_price, total_reviews, average_rating, brands_tracked, categories_tracked}`.
- `getProducts` → `[{id,name,brand,category,price,rating,sentiment,change,interest,color,launch,specs,pros,cons}]`. Backend `ProductResponse` has `id,name,brand,category,price,currency,source,source_url,sku,specs,rating,review_count,created_at,updated_at` — no `sentiment`, `change`, `color`, `launch`, `pros`, `cons`.
- `getSentiment` → `{distribution, trend:[{date,positive,neutral,negative}], aspects:[{aspect,score}], keywords:[{word,score,tone}], reviews:[{id,author,brand,product,text,rating,sentiment,source,date,helpful}]}`. Backend returns `{product_id, product_name, positive, neutral, negative, total_reviews, average_score, aspect_insights}` for ONE product.
- `getBrandStats` → `[{brand, shareOfVoice, mentions, sentiment, topics, concerns, health}]`. Missing endpoint.
- `getConsumerSegments` → `[{id,name,size,users,spend,loyalty,sensitivity,preferences,color}]`. Missing endpoint.
- `getMarketingTrends` → `[{date, Apple, NVIDIA, Reddit, X, event}]`. Missing endpoint.
- `getCompetitors` → `{brands:[{name,color,share,health}], priceDifferences:[{name,brand,price,baseline,difference}]}`. Missing endpoint.
- `getRecommendations` → `[{id,category,priority,title,detail,metric,confidence,related,route,icon}]`. Backend returns `{product_id, product_name, recommendation, reason, pros, cons, sentiment_score, price_score}`.

CONFIRMED by reading every page and `backend/schemas/*.py`.

### 2.3 Mocks imported by pages even when `VITE_API_URL` is set

| File | Import |
|---|---|
| `src/pages/MarketOverview.jsx:8` | `BRANDS` |
| `src/pages/ProductAnalysis.jsx:9` | `priceHistory` (used directly in the drawer chart) |
| `src/pages/BrandIntelligence.jsx:7` | `BRANDS`, `brandStats` |
| `src/pages/ConsumerInsights.jsx:7` | `segments as segmentMock` (imported, unused) |
| `src/pages/CompetitorAnalysis.jsx:6` | `BRANDS`, `products` |
| `src/components/common.jsx:3` | `BRANDS` (brand colours) |

CONFIRMED by `grep -n "mocks/marketData" src/`.

### 2.4 Hardcoded numbers baked into JSX (not from any API, not even from mocks)

| File:line | Hardcoded |
|---|---|
| `MarketOverview.jsx:25` | eyebrow "MONDAY, FEBRUARY 24, 2025" |
| `MarketOverview.jsx:28` | trending brand NVIDIA, "+34.2% interest this week" |
| `SentimentAnalysis.jsx:25` | distribution `71 / 20 / 9` |
| `SentimentAnalysis.jsx:26` | "84.2k" / "18.6k" reviews analyzed |
| `SentimentAnalysis.jsx:32` | "Positive sentiment is up 4.8% this month" |
| `ConsumerInsights.jsx:11` | `drivers` array (6 factors with scores) |
| `ConsumerInsights.jsx:24` | growth "+8.4% / +4.1% / +6.2%" |
| `MarketingAnalytics.jsx:10-14` | `opportunities` array (3 items) |
| `MarketingAnalytics.jsx:28` | "Trends refreshed 4h ago" |
| `MarketingAnalytics.jsx:29` | KPI row 78.4 / 42.8k / 86 / 28.4% |
| `MarketingAnalytics.jsx:36` | "Where the conversation lives" bars (18600/14200/7800/5100) |
| `MarketingAnalytics.jsx:37` | "Reddit leads conversation share 43.5%" |
| `CompetitorAnalysis.jsx:10-23` | `features`, `matrix`, `activity` arrays |
| `CompetitorAnalysis.jsx:41` | "5 brands tracked" |
| `CompetitorAnalysis.jsx:43` | "NVIDIA leads perceived quality" insight |
| `AIRecommendations.jsx:22` | executive summary headline + paragraph, "84.4% avg. confidence", "82/100 market readiness", "6 pts this month" |
| `BrandIntelligence.jsx:30` | "+3.2 pts this month", "+2.4 pts", "12.8% this month" |
| `BrandIntelligence.jsx:43` | "Positive sentiment is up 3.2 points" |
| `Layout.jsx:15` | nav badge "5" |
| `Layout.jsx:41` | "Northstar Labs / Pro workspace" |
| `Layout.jsx:48` | "All sources connected / LIVE" |
| `Layout.jsx:50` | "Stefan C. / Marketing lead" |
| `Layout.jsx:56` | "Data refreshed 4 min ago" |

CONFIRMED by reading each file.

### 2.5 Database

- `backend/config.py:22` — `DATABASE_URL: str = "sqlite:///./marketpulse.db"`.
- `backend/database/connection.py:22-26` — on any engine error, logs a warning and silently creates `sqlite:///./marketpulse.db`. A wrong MySQL password produces a working-looking app on an empty SQLite file.
- `backend/requirements.txt:9` — `psycopg2-binary` only. **No MySQL driver.**
- `backend/requirements.txt:10` — `alembic`, but no `alembic.ini` and no `migrations/`.
- `backend/database/seeds.py:144-204` — reviews keyed to hardcoded `product_id` 1..5.
- No `docker-compose.yml`, no `.env` (only `.env.example`).

CONFIRMED.

### 2.6 AI / LLM

- No LLM client anywhere. `grep -ri "openai\|anthropic\|openrouter\|llm" backend/` → 0 hits.
- `services/recommendations.py` is threshold logic (pos_pct ≥ 65, price < cat_avg × 0.9, …).
- `services/sentiment_analysis.py` is VADER with a hand-written tech lexicon.
- `connectors/google_trends.py:79-102` — `_estimate_trend` fabricates `score = 88.0` or `72.0` when the real call fails and labels it `"MarketPulse Trend Engine"`.

CONFIRMED.

### 2.7 Data-integrity bugs

| File:line | Bug |
|---|---|
| `services/forecasting.py:36` | `oldest_price = prices[-1]` — the API passes history **ascending** (`analytics.py:94`), so `[-1]` is the newest. `price_change_percentage` is computed newest→current, always ≈0. |
| `data_collection/prices.py:53-71` | `product.price = observed_price` then `"old_price": product.price` — old and new are identical in the response. |
| `connectors/emag.py:167` | `def _clean_price(self, price_raw: str) -> (Optional[float], str):` — a tuple expression, not a type. |
| `data_collection/reviews.py:105` | Dedupe loads every review content for the product into memory; fine at prototype scale, noted. |
| `api/analytics.py:223` | `return get_trends(db=db)` calls the endpoint function directly; works, but bypasses the response model. |

CONFIRMED.

### 2.8 Tests

- `backend/tests/test_api.py` — a `run_tests()` script with `assert` statements, not pytest-discoverable (no `test_` prefix on a zero-arg function). Uses the dev database.
- `backend/tests/test_connectors.py` — `test_connectors()` makes **live network calls** to Hacker News and Google Trends. Not hermetic.
- No frontend tests, no Playwright config, no `playwright.config.*`, no `e2e/`.

CONFIRMED.

### 2.9 Repo hygiene

- `node_modules/` (89.8 MB, 8 520 files) is committed. `.gitignore` lists it, so it was added before the rule.
- No `.github/`, no CI, no tags.
- `README.md:16` documents the mock behaviour honestly but gives instructions that break the app.

CONFIRMED.

## 3. Every module the change would touch (`file:line` at `f8b0b2c`, each read)

| File | What it does today | Change |
|---|---|---|
| `backend/config.py` | settings, SQLite default | MySQL default, explicit required vars |
| `backend/database/connection.py` | engine + silent SQLite fallback | MySQL engine, no fallback, pool tuning |
| `backend/database/models.py` | 4 tables | add columns for the frontend contract (launch, pros/cons, colour, segment, campaign) or derive them |
| `backend/database/seeds.py` | 5 products, 11 reviews, 4 trends, hardcoded ids | idempotent seed keyed by SKU, richer dataset |
| `backend/api/products.py` | CRUD + collectors | add `/compare`, reshape responses |
| `backend/api/analytics.py` | 6 endpoints | reshape 3, add 3 |
| `backend/api/marketing.py` | — | **new** router |
| `backend/schemas/*` | 4 modules | add the frontend DTOs |
| `backend/services/*` | sentiment, forecasting, recommendations | add LLM service, fix forecasting |
| `backend/connectors/google_trends.py` | fabricated fallback | honest unavailable state |
| `backend/requirements.txt` | Postgres driver | add PyMySQL, remove/keep psycopg2 |
| `src/services/api.js` | mock fallback | real HTTP only, all 10 endpoints |
| `src/pages/*.jsx` (8) | hardcoded numbers + mock imports | API-driven |
| `src/components/common.jsx` | `BRANDS` from mocks | brand colours from API |
| `src/components/Layout.jsx` | hardcoded persona/status | API-driven status |
| `src/mocks/marketData.js` | fixtures | delete or keep only as test fixtures |
| `docker-compose.yml` | — | **new** |
| `playwright.config.js`, `e2e/*` | — | **new** |

## 4. Options

| Option | What changes | What stays identical | Risk | Verdict |
|---|---|---|---|---|
| **A. Backend adapts to the frontend** | backend DTOs + 5 new endpoints | the entire UI design | backend grows; some values must be derived (colour, change) | **Recommended** — the UI is the designed product |
| B. Frontend adapts to the backend | 8 pages rewritten | backend | loses the designed UI; weeks of work | Rejected |
| C. Keep mocks, add a toggle | nothing real | everything | the app stays a demo | Rejected — the user asked for no placeholders |
| D. Rewrite both | everything | nothing | highest risk, no benefit | Rejected |

## 5. Recommendation (precise)

Contract-first, in the queue order (QUEUE.md items 1-7). The backend serves exactly the DTOs the pages consume; the frontend loses its mock fallback and every hardcoded number; MySQL runs in Docker; OpenRouter powers the three genuinely-AI surfaces; Playwright + Camoufox prove it end to end.

Derivation rules for fields the DB does not store today (so nothing is fabricated):
- `sentiment` (0-100) = `round((positive_pct + average_score*50) / 1.5)` from stored reviews, or `NULL` when a product has none.
- `change` (% price movement) = from `price_history` first vs latest; `0.0` when fewer than two points.
- `color` = a stable per-brand colour map computed server-side from the brand name hash, with the five known brands pinned.
- `launch` = `NULL` (not measured) unless a spec field carries it; the UI renders "—".
- `pros`/`cons` = derived from aspect sentiment (top positive aspects / top negative aspects); empty arrays when no reviews.
- `mentions` = derived from `reviews` (source, sentiment, date); no invented engagement counts — `engagement` becomes the review's `helpful` proxy or is omitted.
- `keywords` = term frequency over stored review text, weighted by sentiment.
- `consumer-segments`, `competitors`, `marketing trends` = computed from products + reviews + price history; where a value cannot be computed it is `null` and the UI says "not enough data".

## 6. Risks

| # | Risk | Mitigation |
|---|---|---|
| 1 | eMAG HTML scraping breaks (anti-bot, selector drift) | never fabricate; return an explicit `unavailable` status; the UI shows it |
| 2 | Reddit public JSON is rate-limited without auth | same: explicit status, no invented data |
| 3 | OpenRouter free model rate limits (1000 RPD) | cache LLM outputs in the DB; a bounded retry; degrade to the rule-based engine with a visible label |
| 4 | Deriving `sentiment`/`change` from thin data produces misleading numbers | `NULL` + "not enough data" rather than 0 |
| 5 | Schema changes break the existing SQLite file | the user has no production data; a fresh MySQL volume is the baseline |
| 6 | Playwright/Camoufox flakiness | deterministic seed data; assertions on data, not pixels; screenshots as evidence only |

## 7. QUESTIONS for the user

1. **Which side adapts?** The frontend is a finished design; the backend is a data layer. Adapt the backend to serve exactly what the pages consume, or rewrite the pages to fit the backend? — Rec: **backend adapts** (Option A). The UI is the product.
2. **What happens when the backend is down?** Today the app silently shows fake data. Remove the mock fallback entirely so a failure is visible, or keep it behind an explicit `VITE_USE_MOCKS=true` flag for demos? — Rec: **remove it entirely**; a demo flag is how placeholders survive into the final product.
3. **Currency in the UI.** The backend stores RON (eMAG prices); the UI prints `$`. Show RON with `lei`, or convert to USD? — Rec: **show RON/lei** — the data source is Romanian and a conversion rate would be another invented number.
4. **MySQL delivery.** No MySQL is installed on this machine; Docker is running. Run MySQL 8 in a Docker container on host port 3307 (leaving 3306 free), or install MySQL natively? — Rec: **Docker** — reproducible, no machine changes, one `docker compose up`.
5. **What counts as "no placeholders" for the demo persona?** The sidebar shows "Northstar Labs", "Stefan C.", "All sources connected", "Data refreshed 4 min ago", and a nav badge "5". Make them real (workspace from config, source status from the last successful collection, badge from the recommendation count), or remove the ones with no data behind them? — Rec: **make them real where data exists, remove the rest**.
6. **LLM scope.** Which surfaces should call OpenRouter? — Rec: **AI Recommendations** (executive summary + per-item rationale), the **product review summary** in the drawer, and **marketing opportunities**. Sentiment stays VADER (deterministic, free, already working).
7. **OpenRouter model.** The user picks a free model (1000 RPD). Please give the exact model id (e.g. `meta-llama/llama-3.3-70b-instruct:free`) and the key when you are ready. — Rec: none from me; this is the user's choice.
8. **Push and PR.** Nothing is pushed today. Work locally and show the diff, or push a branch and open a PR against `main`? — Rec: **local first**, push when the gate is green and you have seen it work.
9. **`.orchestration/`.** It is currently gitignored. Keep it local, or commit it so the team sees the queue and the specs? — Rec: **keep it local** for now.

## 8. CONFIRMED / UNVERIFIED / NOT DONE

- CONFIRMED: every path, line number and shape above was read in the file named.
- CONFIRMED: MySQL is absent from this machine (`Get-Service *mysql*` empty, no `mysql.exe`, nothing on 3306); Docker 29.8.0 is running.
- CONFIRMED: Python 3.13.7 has fastapi/uvicorn/SQLAlchemy/pydantic/httpx/bs4/pytest/playwright; it lacks PyMySQL, vaderSentiment, pytrends, pandas, numpy, scikit-learn, lxml.
- UNVERIFIED: whether eMAG still serves the selectors in `connectors/emag.py` (no live call made — budget 0).
- UNVERIFIED: whether Reddit's public JSON still answers without auth from this IP.
- NOT DONE: no live external call of any kind; no code changed; no database created.

## 9. Left on disk (nothing deleted; no process left running)

- `D:\Projects2\adobe hackathon\aplicatie-hackathon-adobe` — the clone at `f8b0b2c`.
- `.orchestration/` — WORKING-NOTES.md, QUEUE.md, HANDOFF-2026-11-07.md, WORKING-NOTES-ARCHIVE.md, specs/.
- `CLAUDE.md` — created with the managed block.
- `.gitignore` — extended (`.orchestration/`, Playwright outputs, `mysql-data/`).
- No ports opened, no containers started.

by FiredMosquito831

## USER DECISIONS (2026-11-07, binding)

The user answered the four structural questions and accepted every recommendation:

1. **Which side adapts?** → **Backend adapts** (Option A). The backend serves exactly the DTOs the pages consume. The UI design is not rewritten.
2. **Mock fallback?** → **Remove it entirely.** No `VITE_USE_MOCKS` flag. A backend failure shows `ErrorState`.
3. **Currency?** → **RON / lei.** No exchange-rate conversion. The UI prints `lei`, the backend stores `RON`.
4. **MySQL delivery?** → **Docker, host port 3307.** 3306 stays free.

Resolved by the orchestrator under the stated assumptions, to be confirmed if wrong:
5. Demo persona ("Northstar Labs", "Stefan C.", "All sources connected", "Data refreshed 4 min ago", badge "5") → made real from data where data exists; removed where it does not.
6. LLM scope → AI Recommendations (executive summary + per-item rationale), the product review summary in the drawer, and marketing opportunities. Sentiment stays VADER.
7. OpenRouter model and key → the user supplies both; the service degrades visibly to the rule-based engine when the key is absent.
8. Push and PR → local first; push only on the user's go.
9. `.orchestration/` → stays local (gitignored).

by FiredMosquito831
