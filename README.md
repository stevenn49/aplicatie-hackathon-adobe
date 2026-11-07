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


`backend/` is a Python service that generates marketing advice from the dashboard data using a local model on [Ollama](https://ollama.com). Groq and Gemini (free API keys) are supported as alternatives via `AI_PROVIDER`.

### Setup

1. Install [Ollama](https://ollama.com) and pull a model: `ollama pull llama3.2`.
2. Install and configure the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
# AI_PROVIDER=ollama is the default; set AI_MODELS to pin a model
```

### Command-line script

```bash
python marketing_advisor.py "How should Samsung respond to charging-speed complaints?"
python marketing_advisor.py --brand Sony "Plan a launch campaign for the WH-1000XM6"
python marketing_advisor.py --recommendations --brand NVIDIA   # JSON in the dashboard's format
python marketing_advisor.py --chat                             # interactive conversation
python marketing_advisor.py --list-models                      # models available from the provider
```

### Connect it to the dashboard

```bash
uvicorn server:app --reload --port 8000     # from backend/
```

Then set `VITE_AI_API_URL=http://localhost:8000` in `.env.local` and run `npm run dev`. The AI Recommendations page now shows model-generated recommendations (cached for 10 minutes). If the backend is unavailable, the page falls back to the mock recommendations.

Endpoints: `GET /analytics/recommendations?category=Marketing&brand=Apple`, `POST /ai/advice` (`{"question": "...", "brand": "Apple"}`), `GET /health`.

### In-app assistant chat (Ollama)

Every page has an **Ask AI** button (bottom right) and every chart has an **Analyse** button. The assistant sees the data of all charts on the current page plus the active filters, and can analyse charts, suggest marketing ideas, plan campaigns, build content calendars, write copy, compare competitors, analyse sentiment and summarise pages. Follow-up questions keep the conversation context.

Run it fully locally with [Ollama](https://ollama.com):

```bash
ollama pull llama3.2                       # or a bigger model, e.g. llama3.1:8b
# backend/.env
AI_PROVIDER=ollama
AI_MODELS=llama3.2
# .env.local
VITE_AI_API_URL=http://localhost:8000
```

How it works (`backend/assistant.py`, endpoint `POST /ai/chat`, streamed plain text):
1. Charts register their rows with the chat (`ChartCard data={...}` or `<ChartData />`, see `src/context/ChatContext.jsx`).
2. The backend detects the intent of the message and picks an answer format.
3. For each chart it pre-computes exact facts (rankings, gaps, averages, % change, peaks), so small models quote correct numbers instead of doing arithmetic.
4. Prompt = role + market data snapshot + page/filters + chart facts and data + task; when analysing a single chart only that chart is sent. Ollama is called with an 8k context (`OLLAMA_NUM_CTX`).

The model reads `backend/market_data.json`, a static snapshot that predates the MySQL integration. It is **not** connected to the live database: the assistant's narrative is grounded in that file, while the numbers on the dashboard come from MySQL. Regenerate it, or point the assistant at the API, if you need the two to agree. To pin specific models, set `AI_MODELS` in `backend/.env` (comma-separated, tried in order).

**Note on ports.** The main API runs on **8010** (port 8000 is taken on the development machine). The separate AI service in `backend/server.py` is a different app and defaults to 8000; set `VITE_AI_API_URL` to wherever you start it. If both must run, start the AI service on another port, e.g. `uvicorn server:app --port 8020`.
