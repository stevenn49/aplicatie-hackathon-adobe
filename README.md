# MarketPulse AI

A responsive market intelligence dashboard for tracking products, brands, customer sentiment, and marketing signals across the tech industry.

## Run locally

```bash
npm install
npm run dev
```

Vite prints the local URL after the development server starts. Create a production build with `npm run build`, or preview that build with `npm run preview`.

## Mock data and FastAPI integration

All dashboard data is served by `src/services/api.js`. Its functions return realistic fixtures from `src/mocks/marketData.js` after a short simulated delay. To use the FastAPI service, set `VITE_API_URL` to its base URL (copy `.env.example` to `.env.local`) and update the endpoint paths and any request parameters in `src/services/api.js` to match the backend contract. The UI can continue using the same service functions.

## Routes

- `/` — Market Overview
- `/products` — Product Analysis and comparisons
- `/brands` — Brand Intelligence
- `/sentiment` — Sentiment Analysis
- `/consumers` — Consumer Insights
- `/marketing` — Marketing Analytics
- `/competitors` — Competitor Analysis
- `/recommendations` — AI Recommendations

## AI marketing advisor (Ollama)

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

The model reads `backend/market_data.json`, a snapshot of `src/mocks/marketData.js`. Regenerate it if the mock data changes. To pin specific models, set `AI_MODELS` in `backend/.env` (comma-separated, tried in order).
