# MarketPulse AI

Market intelligence for technology products: prices, reviews, sentiment, brand
perception and competitive positioning, computed from a real MySQL database and
served to a React dashboard.

Everything the dashboard shows is computed from stored rows. There is no mock
fallback and no placeholder number: when a value cannot be derived, the UI says
"not enough data".

---

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| Node.js | 18+ | ships npm |
| Python | 3.11+ | 3.13 tested |
| MySQL | 8.0+ | either Docker (recommended) or a native install |
| Docker Desktop | any recent | only for the Docker database mode |

---

## Cold setup

### Windows (PowerShell)

```powershell
git clone https://github.com/stevenn49/aplicatie-hackathon-adobe.git
cd aplicatie-hackathon-adobe
.\scripts\setup.ps1
```

### macOS / Linux

```bash
git clone https://github.com/stevenn49/aplicatie-hackathon-adobe.git
cd aplicatie-hackathon-adobe
chmod +x scripts/*.sh
./scripts/setup.sh
```

The setup script checks the toolchain, prepares the database, writes
`backend/.env` and `.env.local`, and installs both dependency sets. It is safe to
run again.

### Choosing the database

**Docker (default).** MySQL 8.4 runs in the `marketpulse-mysql` container on host
port **3307**, so port 3306 stays free for a native install.

```bash
docker compose up -d          # start
docker compose logs -f mysql  # logs
docker compose stop           # stop, keep the data
docker compose down -v        # stop and delete the data volume
```

**Native MySQL.** If you already run MySQL locally, point the app at it:

```powershell
.\scripts\setup.ps1 -Database native -DbPort 3306 -DbUser root -DbPassword <your-password>
```

```bash
./scripts/setup.sh --database native --db-port 3306 --db-user root --db-password <your-password>
```

Or edit `DATABASE_URL` in `backend/.env` by hand:

```
DATABASE_URL="mysql+pymysql://USER:PASSWORD@HOST:PORT/marketpulse"
```

The database is **shared** during the prototype: all teammates point at the same
server so everyone sees the same data. Use a local Docker container only for your
own scratch work.

---

## Start

```powershell
.\scripts\start.ps1
```

```bash
./scripts/start.sh
```

| Service | URL |
| --- | --- |
| Dashboard | http://127.0.0.1:5173 |
| API | http://127.0.0.1:8010 |
| API docs (OpenAPI) | http://127.0.0.1:8010/docs |

Port 8010 rather than 8000: some development machines already have a service on
8000. Change it with `-BackendPort` / `--backend-port` and update
`VITE_API_URL` in `.env.local` to match.

### Manual start

```bash
# terminal 1
cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8010

# terminal 2
npm run dev
```

---

## Optional: enable the LLM surfaces

The AI Recommendations executive summary, the product review summary and the
marketing opportunities can be written by a model through
[OpenRouter](https://openrouter.ai). Without a key the app still works: those
three surfaces use the deterministic engine and the API reports
`"source": "derived"` instead of `"llm"`.

Add to `backend/.env`:

```
OPENROUTER_API_KEY="sk-or-v1-..."
OPENROUTER_MODEL="<a free model id from https://openrouter.ai/models?max_price=0>"
```

Responses are cached in the `llm_cache` table for 12 hours, so repeated page
loads do not spend the free-tier quota.

**Never commit `backend/.env` or `.env.local`.** Both are gitignored.

---

## Project layout

```
backend/
  api/            products, analytics, marketing routers
  connectors/     eMAG, Reddit, X, Google Trends, Hacker News
  data_collection/ review, price and trend collectors
  database/       SQLAlchemy models, MySQL connection, seed data
  schemas/        Pydantic models (ORM contracts + dashboard DTOs)
  services/       sentiment, forecasting, recommendations, analytics, LLM
  tests/          pytest suite
src/
  components/     layout, charts, shared UI
  constants/      product scope (brand list, formatters)
  context/        filters and theme
  pages/          the eight dashboard pages
  services/       the single HTTP layer (api.js)
e2e/              Playwright end-to-end tests
scripts/          setup and start scripts
```

---

## Tests

```bash
# backend (uses a scratch database, drops it afterwards)
cd backend && python -m pytest tests -q

# frontend build
npm run build

# end-to-end (needs the stack running)
npx playwright install chromium
npx playwright test
```

---

## Routes

| Path | Page |
| --- | --- |
| `/` | Market Overview |
| `/products` | Product Analysis and comparison |
| `/brands` | Brand Intelligence |
| `/sentiment` | Sentiment Analysis |
| `/consumers` | Consumer Insights |
| `/marketing` | Marketing Analytics |
| `/competitors` | Competitor Analysis |
| `/recommendations` | AI Recommendations |

---

## Troubleshooting

**`DATABASE_URL must be a MySQL URL`** — `backend/.env` still holds the old
SQLite value. Re-run the setup script or edit the line.

**`Can't connect to MySQL server`** — the container is not running
(`docker compose up -d`) or the native server is stopped. Check with
`docker ps` / `mysqladmin ping`.

**The dashboard shows "We couldn't load this data"** — the API is unreachable.
Check `http://127.0.0.1:8010/health` and that `VITE_API_URL` in `.env.local`
matches the backend port.

**`Port 8010 is already in use`** — pass a different port to the start script and
update `VITE_API_URL`.

**eMAG import returns 503** — the public catalogue is rate-limiting or its page
layout changed. The API reports this explicitly rather than inventing a product.
