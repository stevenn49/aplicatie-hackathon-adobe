# MarketPulse AI — brief complet

*Ce este, ce oferă, cum funcționează, ce e stricat și ce valoare are. Scris pe 2026-11-07, după un audit linie-cu-linie al întregului cod.*

---

## 1. Ce este proiectul, în două fraze

MarketPulse AI este un dashboard de **market intelligence pentru industria tech**: adună date publice despre produse, prețuri, recenzii și discuții online, le trece prin analiză de sentiment și statistică, și le transformă în decizii de marketing și produs.

Nu este un simplu monitor de prețuri. Încearcă să răspundă la întrebarea „**ce ar trebui să facem acum?**” — nu doar „ce se întâmplă?”.

---

## 2. Ce oferă concret — cele opt secțiuni

Aplicația are opt pagini, fiecare cu o întrebare de business proprie:

| # | Pagina | Întrebarea la care răspunde | Ce arată |
|---|---|---|---|
| 1 | **Market Overview** | „Ce se mișcă pe piață acum?” | 4 KPI-uri, evoluția interesului pe brand, share of voice (donut), top movers (cele mai mari variații de preț), mențiuni recente |
| 2 | **Product Analysis** | „Care produs merită și de ce?” | Tabel sortabil cu 10 produse (preț, rating, sentiment, trend de preț), comparație side-by-side pentru 2-4 produse cu radar chart, drawer de detaliu cu istoric de preț, forecast, specificații, pros/cons extrase din recenzii |
| 3 | **Brand Intelligence** | „Unde stă fiecare brand?” | Brand health score, share of voice, evoluție în timp, teme lăudate vs teme criticate |
| 4 | **Sentiment Analysis** | „Cum se simt clienții, nu doar ce spun?” | Distribuție pozitiv/neutru/negativ, trend săptămânal, sentiment pe aspecte (baterie, cameră, ecran…), nor de cuvinte cheie, explorator de recenzii cu filtrare |
| 5 | **Consumer Insights** | „Cine cumpără și de ce?” | Cinci segmente de consumatori, drivers de achiziție, hartă sensibilitate-la-preț vs loialitate, preferințele fiecărui segment |
| 6 | **Marketing Analytics** | „Unde e următoarea oportunitate?” | Interes de piață în timp, volum de mențiuni pe sursă, timeline de campanii, carduri de oportunități |
| 7 | **Competitor Analysis** | „Cum arată piața din toate unghiurile?” | Poziționare competitivă (preț vs calitate percepută), diferențe de preț față de mediana categoriei, matrice de features pe brand, activitate recentă a concurenței |
| 8 | **AI Recommendations** | „Ce facem concret, în ordinea impactului?” | Sumar executiv, recomandări prioritizate (High/Medium/Low) cu metrică, confidence și link către dovadă |

**Elemente transversale:** bară de filtre globală (brand, interval 7d/30d/90d/1y, sursă), căutare globală cu `Ctrl+K`, temă dark/light, sidebar colapsabil, design responsive.

---

## 3. Cum funcționează — arhitectura

```
SURSE EXTERNE                 CONECTOARE              PROCESARE              API                    UI
─────────────────             ───────────             ──────────             ───                    ──
eMAG (HTML public)    ──┐
Reddit (JSON public)  ──┤     rate-limiting           VADER sentiment   ──┐
Hacker News (Algolia) ──┼──▶  + parsing HTML    ──▶   extragere aspecte   ├──▶  FastAPI   ──▶  React + Vite
X/Twitter (API v2)    ──┤     + deduplicare           statistici preț     │    + MySQL        + Recharts
Google Trends         ──┘                             forecast liniar   ──┘
                                                      recomandări
```

### Stack

- **Frontend:** React 18, Vite 6, React Router 6, Recharts 2, lucide-react. Fără TypeScript. Un singur fișier CSS de ~70 KB.
- **Backend:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.
- **Bază de date:** MySQL 8.4 (în Docker pe portul 3307).
- **NLP:** VADER cu lexic tehnic custom („lag”, „overheating”, „snappy”, „crisp” etc.).
- **LLM:** OpenRouter (opțional, pentru sumarul executiv și rezumatul recenziilor).

### Modelul de date

Patru tabele principale:

- `products` — produs, brand, categorie, preț, rating, specificații (JSON), sursă, URL
- `price_history` — fiecare punct de preț în timp
- `reviews` — text, autor, rating, scor de sentiment, etichetă, aspecte detectate (JSON)
- `trend_metrics` — scoruri de trend pe categorie

Plus `llm_cache` — cache pentru răspunsurile OpenRouter, ca să nu arzi cele ~1000 de requesturi/zi gratuite.

### Fluxul unei analize

1. Un conector aduce text brut (recenzii, postări, comentarii).
2. Textul e curățat (HTML, URL-uri, spații) și deduplicat.
3. VADER calculează un scor compus între -1 și +1 → etichetă pozitiv/neutru/negativ.
4. Un al doilea pas extrage **aspectele**: baterie, cameră, ecran, performanță, preț, construcție, software, audio — fiecare cu propriul sentiment.
5. Aspectele se agregă pe produs și pe brand → pros/cons, teme lăudate, teme criticate.
6. Statisticile de preț (min/max/medie/variație) și forecast-ul liniar se calculează din istoric.
7. Recomandările se generează din praguri reale (gap de preț față de mediană, sentiment, aspect slab).
8. Opțional, LLM-ul rescrie formularea — dar **niciodată cifrele**.

---

## 4. Starea reală la momentul auditului

Aici e partea importantă, și e neplăcută.

### 4.1 Aplicația era 100% mock

`src/services/api.js` avea linia:

```js
const API_URL = import.meta.env.VITE_API_URL || "";
if (!API_URL) return delay(fallback);
```

Adică: **dacă nu setezi `VITE_API_URL`, frontendul servește date inventate** din `src/mocks/marketData.js` după o întârziere simulată de 360 ms. Aplicația arată perfect, cu zero backend pornit.

Mai rău: `.env.example` din rădăcină conținea `VITE_API_URL=http://localhost:8000`. Dacă urmai instrucțiunea din README și copiai fișierul, **fiecare pagină crăpa**, pentru că frontendul cerea `/analytics/overview` iar backendul servea `/api/analytics/overview`.

### 4.2 Backendul și frontendul nu au fost niciodată conectate

Frontendul cerea **10 endpointuri**. Backendul avea **5**. **Niciunul** nu se potrivea ca formă.

| Frontend cerea | Backend avea | Verdict |
|---|---|---|
| `GET /analytics/overview` | `GET /api/analytics/overview` | cale + formă greșite |
| `GET /products` | `GET /api/products/` | cale + formă greșite |
| `GET /products/compare?ids=` | — | **lipsea** |
| `GET /products/{id}` | `GET /api/products/{id}` | cale + formă greșite |
| `GET /analytics/brands` | — | **lipsea** |
| `GET /analytics/sentiment` | `GET /api/analytics/sentiment?product_id=` | parametru obligatoriu + formă |
| `GET /analytics/consumer-segments` | — | **lipsea** |
| `GET /marketing/trends` | — | **lipsea** (nu exista router de marketing) |
| `GET /analytics/competitors` | — | **lipsea** |
| `GET /analytics/recommendations` | `GET /api/analytics/recommendations` | cale + formă greșite |

Concret: backendul returna `{total_products, average_price, total_reviews}` iar pagina aștepta `{kpis, evolution, mentions, topMovers}`. Două contracte diferite, scrise de oameni diferiți, fără un test care să le lege.

### 4.3 Numere inventate direct în JSX

Dincolo de mock-uri, o parte din cifrele afișate erau hardcodate în componente — nu veneau nici măcar din mock:

| Fișier | Ce era inventat |
|---|---|
| `MarketOverview.jsx` | data „MONDAY, FEBRUARY 24, 2025”, trending NVIDIA „+34.2%” |
| `SentimentAnalysis.jsx` | distribuția 71/20/9, „84.2k reviews”, „+4.8% this month” |
| `ConsumerInsights.jsx` | array-ul `drivers` (6 factori cu scoruri), creșteri „+8.4%/+4.1%/+6.2%” |
| `MarketingAnalytics.jsx` | KPI-uri 78.4 / 42.8k / 86 / 28.4%, barele 18600/14200/7800/5100, „Reddit 43.5%”, „refreshed 4h ago” |
| `CompetitorAnalysis.jsx` | matricea de features, array-ul `activity`, „5 brands tracked” |
| `AIRecommendations.jsx` | sumarul executiv întreg, „84.4% avg. confidence”, „82/100 market readiness” |
| `BrandIntelligence.jsx` | „+3.2 pts this month”, „+2.4 pts”, „12.8% this month” |
| `Layout.jsx` | „Northstar Labs”, „Stefan C.”, badge „5”, „All sources connected”, „Data refreshed 4 min ago” |

### 4.4 Baza de date

- Default-ul era **SQLite**, nu MySQL, deși specificația cerea PostgreSQL.
- `database/connection.py` avea un **fallback silențios**: dacă conexiunea eșua, crea un fișier SQLite gol. O parolă greșită la MySQL arăta ca o aplicație funcțională cu zero date.
- **Nu exista driver MySQL** în `requirements.txt` — doar `psycopg2` (PostgreSQL).
- `alembic` era în requirements, dar fără `alembic.ini` și fără `migrations/`. Unealtă pe jumătate instalată.
- Seed-ul folosea `product_id` hardcodat 1…5 — fragil.

### 4.5 Bug-uri de integritate a datelor

| Fișier | Bug | Efect |
|---|---|---|
| `services/forecasting.py:36` | `oldest_price = prices[-1]` | istoricul vine sortat crescător, deci `[-1]` e cel **mai nou**. Variația de preț se calcula de la cel mai nou punct la curent → mereu ≈ 0% |
| `data_collection/prices.py:70` | `old_price: product.price` după `product.price = observed_price` | `old_price` și `new_price` erau **identice** în răspuns |
| `connectors/google_trends.py:79` | `_estimate_trend` returna 88.0 sau 72.0 inventat, etichetat „MarketPulse Trend Engine” | Date false prezentate ca măsurători |
| `connectors/emag.py:167` | `-> (Optional[float], str)` | Tuple expression, nu type hint |

### 4.6 Testare

- `backend/tests/test_api.py` — script cu `print()`, nu e descoperit de pytest (funcția `run_tests()` nu începe cu `test_`). Folosea baza de date de dezvoltare.
- `backend/tests/test_connectors.py` — făcea **apeluri live** către Hacker News și Google Trends. Nu e hermetic.
- Zero teste de frontend. Zero Playwright. Zero CI.

### 4.7 Igienă de repo

- `node_modules/` (89.8 MB, 8 520 fișiere) era **comis în git**.
- Fără `.github/`, fără CI, fără tag-uri, fără release-uri.
- README-ul descria onest comportamentul mock, dar dădea instrucțiuni care stricau aplicația.

---

## 5. Valoarea proiectului

Ca să fiu corect: **problemele sunt de integrare, nu de concept.** Fundația e bună.

### Ce e genuinely valoros

**1. Design-ul UI este de nivel produs comercial.** Nu arată ca un hackathon. Ierarhie vizuală clară, tipografie (DM Sans + Space Grotesk), paletă coerentă, dark/light, responsive, stări de loading/empty/error, accesibilitate (`aria-label`, `role`, focus). Cele opt pagini au fiecare o identitate proprie, nu sunt template-uri.

**2. Modelul de date este corect gândit.** Separarea produs / istoric preț / recenzii / trenduri e exact ce trebuie. Aspectele stocate ca JSON per recenzie permit analiză pe features fără un al doilea pipeline NLP.

**3. Conectoarele sunt reale, nu stub-uri.** eMAG chiar parsează HTML public cu rate-limiting politicos. Reddit chiar folosește endpointurile `.json`. Hacker News Algolia chiar funcționează fără auth. Există conștientizarea că eMAG Seller API nu e disponibil și s-a mers pe date publice.

**4. NLP-ul are sens pentru domeniu.** Lexicul custom (`lag`, `overheating`, `snappy`, `crisp`) arată că cineva s-a gândit la textul tehnic, nu doar a aruncat un model generic.

**5. Extragerea pe aspecte este diferențiatorul real.** „Sentiment 72/100” nu spune nimic. „Bateria e lăudată, prețul e criticat” spune tot. Aici e valoarea de produs.

**6. Arhitectura backend e curată.** Routere separate, servicii separate, schema Pydantic, dependency injection. Ușor de extins.

**7. Povestea de business e completă.** Cele cinci direcții (Product / Consumer / Marketing / Competitive / AI) acoperă ciclul întreg de decizie, nu doar o bucată.

### Ce lipsește ca să fie produs

- **Nicio sursă de date reală conectată la UI.** Tot ce se vede venea din fixturi.
- **Niciun LLM.** Produsul se numește „AI” dar recomandările erau `if pos_pct >= 65`.
- **Nicio dovadă că merge.** Zero teste end-to-end.
- **Nicio persistență reală.** SQLite efemer.

---

## 6. Verdict

| Dimensiune | Notă | Comentariu |
|---|---|---|
| Concept și poziționare | **9/10** | Clar, diferențiat, cu poveste de business |
| Design UI | **9/10** | Nivel comercial, nu hackathon |
| Arhitectură backend | **7/10** | Curată, dar contractul nu se potrivea cu UI-ul |
| Integrare frontend ↔ backend | **1/10** | Nu existau conectate |
| Realitate a datelor | **2/10** | Mock implicit + numere hardcodate în JSX |
| Testare | **1/10** | Scripturi cu `print`, zero e2e |
| Pregătire pentru demo | **3/10** | Arată perfect, dar nu dovedește nimic |

**Concluzia onestă:** era un **prototip de design foarte bun lipit de un backend foarte bun, cu un gol în mijloc**. Ambele jumătăți existau și erau de calitate. Nimeni nu le conectase.

Vestea bună: golul e mecanic, nu creativ. Nu trebuie reinventat nimic — trebuie construit contractul dintre ele, scos mock-ul, înlocuite cifrele hardcodate cu calcule reale, și dovedit cu teste că merge.

---

## 7. Ce s-a schimbat deja în această sesiune

| Zonă | Înainte | Acum |
|---|---|---|
| Bază de date | SQLite implicit + fallback silențios | MySQL 8.4 în Docker (port 3307), fără fallback, eroare explicită |
| Endpointuri | 5, forme diferite | 10, exact forma cerută de UI |
| `/api/analytics/brands` | lipsea | implementat, calculat din recenzii |
| `/api/analytics/consumer-segments` | lipsea | implementat, derivat din aspectele recenziilor |
| `/api/analytics/competitors` | lipsea | implementat, cu matrice de features |
| `/api/marketing/trends` | lipsea (fără router) | router nou + dashboard complet |
| `/api/products/compare` | lipsea | implementat |
| Sentiment | per produs, cu `product_id` obligatoriu | agregat pe toate recenziile, filtrabil |
| Recomandări | reguli fără context | 13 recomandări reale + sumar executiv + LLM opțional |
| Seed | 5 produse, id-uri hardcodate | 10 produse, 48 recenzii, idempotent pe SKU |
| Bug forecast | variație mereu ≈ 0% | corectat (primul punct din istoric) |
| Bug `old_price` | identic cu `new_price` | corectat |
| Google Trends | scor inventat 88/72 | „indisponibil”, fără fabricație |
| LLM | inexistent | serviciu OpenRouter cu cache în DB și degradare onestă |
| `requirements.txt` | driver Postgres, pachete nefolosite | driver MySQL, curățat |

**Ce s-a terminat în continuare:** mock-urile au fost scoase complet din frontend (`src/mocks/` nu mai există, `api.js` nu mai are fallback), toate cifrele hardcodate au fost înlocuite cu valori calculate din baza de date, iar suita de teste acoperă acum backendul (56 teste pytest) și toate cele opt pagini (32 teste Playwright).

---

## 8. Cum rulezi proiectul

### Setup complet, o singură dată

```powershell
# Windows
.\scripts\setup.ps1
```

```bash
# macOS / Linux
./scripts/setup.sh
```

Scriptul verifică toolchain-ul, pornește baza de date, scrie `backend/.env` și `.env.local`, și instalează dependențele. Se poate rula de mai multe ori.

### Pornire

```powershell
.\scripts\start.ps1
```

```bash
./scripts/start.sh
```

### Pornire manuală

```bash
# 1. Baza de date (Docker)
docker compose up -d

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env      # ajustează DATABASE_URL dacă folosești MySQL nativ
python -m uvicorn main:app --host 127.0.0.1 --port 8010

# 3. Frontend
npm install
npm run dev
```

Documentația API: `http://127.0.0.1:8010/docs`

### Teste

```bash
cd backend && python -m pytest tests -q     # 56 teste
npx playwright test                          # 32 teste end-to-end
npm run build                                # build de producție
```

**Notă pentru colegi:** baza de date este partajată în timpul prototipului. Fiecare poate folosi Docker (port 3307) sau MySQL instalat nativ (port 3306) — se schimbă doar `DATABASE_URL` în `backend/.env`. Restul aplicației nu se atinge.

---

*Document generat din auditul codului la commit-ul `f8b0b2c`, actualizat cu modificările din sesiunea curentă.*
