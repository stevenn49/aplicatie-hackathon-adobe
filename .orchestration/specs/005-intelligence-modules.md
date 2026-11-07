# INVESTIGATION — Intelligence modules: feasibility, data, and build order (2026-11-07, read-only)

Written by a read-only investigator. No commits, no code edits, no service starts, no live external calls. The only file written is this spec. CONFIRMED = read the exact line or ran a read-only query and the output is shown; UNVERIFIED = inferred from reading; NOT DONE = skipped, and why.

The user's requirements are quoted verbatim in §1. They are the source of truth: ten named modules, eight additional ideas, and full product CRUD from the UI.

---

## 0. Answer in five lines

1. **Seven of the ten modules can produce real, computed output with today's data, several of them only partially** (10 products, 48 reviews, 40 price points, 5 brands): Review Mining (ABSA already exists), Brand Health Monitor, Price Intelligence, Competitor Benchmarking, Product Radar, Trend Discovery, and Automated Business Reports (on demand).
2. **The three modules whose core promise cannot be met honestly today**: Marketing Campaign Lab and its simulator (no campaign history), Customer Segmentation as *customer* segmentation (48 reviews, 48 distinct authors, no customer identity), and the anomaly-detection / multi-retailer parts of Price Intelligence (4 price points per product, one retailer, a smooth seeded decline with no anomalies).
3. **The single biggest gap is not analytics — it is product CRUD in the UI.** The backend already has create, update, delete and eMAG import; `src/services/api.js` exposes none of them and `ProductAnalysis.jsx` has no add/edit/delete control.
4. **The ML/export libraries are installed globally but not declared**: scikit-learn 1.9.0, numpy 2.4.2, pandas 3.0.1, scipy 1.17.1, reportlab 4.4.10, python-pptx 1.0.2, openpyxl 3.1.5, matplotlib 3.10.8. `requirements.txt:36` explicitly says pandas/numpy/scikit-learn were removed, so a teammate's cold setup would not install them.
5. **Recommended order**: CRUD first, then the four data-real modules (Review Mining, Brand Health, Price Intelligence, Competitor Benchmarking), then the composite scores (Product Radar, Trend Momentum, Opportunity Score), then reports, then ML/campaigns last with explicit "exploratory" labels.

---

## 1. The problem as reported and the reproduction

### 1.1 The user's requirements (verbatim, Romanian)

> **1. Product Radar** – monitorizarea pieței de produse. Prioritate ridicată.
> Un modul care monitorizează permanent produsele și modificările apărute pe piață. Ce ar putea face:
> - Monitorizarea prețurilor produselor.
> - Identificarea produselor nou lansate.
> - Compararea specificațiilor tehnice.
> - Identificarea reducerilor.
> - Monitorizarea ratingurilor.
> - Identificarea schimbărilor în oferta concurenților.
> Exemplu: Dacă NVIDIA lansează un produs nou, MarketPulse AI îl poate introduce în categoria relevantă și îl poate compara cu produsele concurente.
> Un indicator interesant ar fi **Product Competitiveness Score**, calculat din preț, specificații, rating și alte criterii configurabile.
>
> **2. Review Mining** – extragerea informațiilor din recenzii. Prioritate foarte ridicată.
> Aici putem construi ceva foarte interesant din punct de vedere al NLP. Nu ne limităm la clasificarea recenziilor în pozitive, negative și neutre. Extragem motivele pentru care oamenii apreciază sau critică un produs.
> De exemplu, pentru un laptop:
> | Caracteristică | Sentiment identificat |
> | Performanță | Pozitiv |
> | Autonomie | Negativ |
> | Design | Pozitiv |
> | Temperatură | Negativ |
> | Preț | Mixt |
> Putem introduce **Aspect-Based Sentiment Analysis (ABSA)**.
> Mai mult, putem identifica automat problemele recurente:
> - Bateria se descarcă rapid.
> - Dispozitivul se supraîncălzește.
> - Calitatea construcției este apreciată.
> - Raportul calitate-preț este criticat.
> Acest modul ar putea fi extrem de util pentru departamentele de product development și customer experience.
>
> **3. Competitor Benchmarking** – comparație competitivă.
> Aș construi o componentă în care utilizatorul poate selecta două sau mai multe companii și poate compara performanța lor pe mai multe dimensiuni. De exemplu, Apple vs Samsung:
> - Brand sentiment.
> - Product ratings.
> - Price positioning.
> - Customer satisfaction.
> - Online popularity.
> - Review volume.
> - Product innovation indicators.
> Putem utiliza și o diagramă radar pentru a evidenția diferențele dintre companii. Un element interesant ar fi **Competitive Positioning Map**, care poziționează brandurile în funcție de preț și percepția consumatorilor.
>
> **4. Trend Discovery** – identificarea tendințelor pieței. Prioritate ridicată.
> Acest modul ar analiza evoluția interesului pentru produse, branduri și categorii. Exemple:
> - Creșterea interesului pentru AI laptops.
> - Evoluția popularității plăcilor video NVIDIA.
> - Interesul pentru smartphone-uri pliabile.
> - Schimbarea preferințelor pentru anumite categorii de produse.
> Putem introduce un **Trend Momentum Score**, care să combine:
> - Evoluția interesului în timp.
> - Volumul mențiunilor online.
> - Ritmul de creștere a recenziilor.
> - Evoluția căutărilor.
> Important: indicatorul trebuie să fie transparent și calculat pe baza datelor efectiv disponibile.
>
> **5. Marketing Campaign Lab** – laborator de campanii.
> Aici utilizatorul ar putea construi și evalua campanii de marketing. Funcționalități:
> - Definirea obiectivelor campaniei.
> - Stabilirea publicului țintă.
> - Alegerea canalelor de promovare.
> - Alocarea bugetului.
> - Stabilirea KPI-urilor.
> - Compararea mai multor variante de campanii.
> - Evaluarea rezultatelor după implementare.
> O funcționalitate suplimentară ar fi un **Campaign Simulator**. Utilizatorul poate compara două scenarii:
> - Campania A: buget mai mare pentru social media.
> - Campania B: buget mai mare pentru influencer marketing.
> Aplicația poate estima rezultatele folosind ipoteze și date istorice, dacă există. Nu trebuie să prezinte estimările ca rezultate garantate.
>
> **6. Customer Segmentation** – segmentarea consumatorilor.
> Aici putem utiliza algoritmi de Machine Learning, nu doar AI generativ. De exemplu, putem grupa consumatorii după:
> - Sensibilitatea la preț.
> - Preferințele de brand.
> - Frecvența achizițiilor.
> - Preferințele tehnologice.
> - Ratingurile oferite.
> - Interesul pentru anumite caracteristici.
> Algoritmi posibili:
> - K-Means.
> - Hierarchical Clustering.
> - DBSCAN.
> - PCA pentru reducerea dimensionalității și vizualizare.
> Rezultatul ar putea fi:
> | Segment | Caracteristică dominantă |
> | Premium Buyers | Preferă produse premium |
> | Price-Sensitive | Sensibili la preț |
> | Performance Seekers | Caută performanță |
> | Brand Loyalists | Preferă anumite branduri |
> Companiile ar putea utiliza aceste segmente pentru campanii diferențiate.
>
> **7. Price Intelligence** – analiza competitivității prețurilor.
> Un modul dedicat evoluției prețurilor și poziționării comerciale. Funcționalități:
> - Istoric de prețuri.
> - Comparații între comercianți.
> - Identificarea fluctuațiilor.
> - Detectarea reducerilor.
> - Calcularea diferențelor procentuale.
> - Compararea prețului cu ratingul produsului.
> O funcționalitate interesantă ar fi **Price Anomaly Detection**. De exemplu, dacă un produs avea un preț mediu de 5.000 lei și apare brusc la 3.500 lei, sistemul semnalează schimbarea. Putem utiliza Isolation Forest sau metode statistice pentru identificarea anomaliilor.
>
> **8. Brand Health Monitor** – sănătatea brandului.
> Acest modul ar monitoriza imaginea unei companii în mediul online. Aș include:
> - Brand sentiment.
> - Share of Voice.
> - Mențiuni pozitive și negative.
> - Evoluția reputației.
> - Temele asociate brandului.
> - Compararea reputației cu principalii concurenți.
> Un indicator foarte interesant este **Share of Voice**. Formula simplificată:
> SOV = (Mențiunile brandului / Mențiunile tuturor brandurilor analizate) × 100
> Astfel, putem vedea ce pondere din conversațiile online despre o anumită categorie aparține fiecărui brand.
> Atenție: Share of Voice calculat din datele noastre reprezintă doar sursele și perioada monitorizate, nu întreaga piață.
>
> **9. Market Opportunity Finder** – identificarea oportunităților comerciale. Idee diferențiatoare.
> Aceasta ar putea fi una dintre cele mai interesante funcționalități ale aplicației. Sistemul caută oportunități care pot fi exploatate de o companie. Exemplu:
> - Un produs are multe recenzii negative privind autonomia.
> - Produsele concurente au prețuri ridicate.
> - Interesul pentru categoria respectivă este în creștere.
> - Consumatorii apreciază performanța, dar critică raportul calitate-preț.
> MarketPulse AI poate identifica o posibilă oportunitate: un produs cu autonomie îmbunătățită și preț competitiv.
> Aș introduce un **Market Opportunity Score**, bazat pe:
> - Cerere estimată.
> - Nivelul concurenței.
> - Nemulțumirile consumatorilor.
> - Poziționarea prețurilor.
> - Evoluția interesului online.
> Nu ar trebui confundat cu o probabilitate garantată de succes comercial.
>
> **10. Automated Business Reports** – rapoarte automate.
> O funcționalitate foarte practică: utilizatorul selectează o companie, o categorie sau un produs și generează un raport. Raportul ar putea conține:
> - Executive Summary.
> - Market Overview.
> - Product Performance.
> - Competitor Analysis.
> - Consumer Sentiment.
> - Marketing Opportunities.
> - Strategic Recommendations.
> Formate de export:
> - PDF.
> - Excel.
> - CSV.
> - PowerPoint.
> Aș include și posibilitatea de a genera rapoarte săptămânale sau lunare.
>
> **11. Alte idei care merită explorate**
> | Funcționalitate | Rol |
> | Competitor Alerts | Notificări când concurența lansează produse sau modifică prețurile |
> | Product Lifecycle Tracker | Monitorizarea etapelor ciclului de viață al produsului |
> | Customer Satisfaction Index | Indicator compozit de satisfacție |
> | Review Authenticity Signals | Identificarea unor tipare suspecte în recenzii |
> | Marketing Budget Optimizer | Distribuirea bugetului în funcție de obiective și rezultate |
> | Keyword Intelligence | Identificarea cuvintelor și subiectelor populare |
> | Product Recommendation Engine | Recomandarea produselor în funcție de preferințe |
> | Executive Dashboard | Vedere centralizată pentru management |

Plus, separately:

> „putem adăuga și căuta extra produse, să manageriem produsele existente etc — e totul legat ok, corect, cum trebuie sau nu?"

### 1.2 What "done" means

A module is "done" only when every number it shows is either (a) computed from stored rows, (b) visibly labelled with its sample size and source, or (c) explicitly `null` / "not enough data". A module that needs data the system does not have is either deferred or built as an **assumption calculator** whose inputs are the user's and whose formulas are visible — never as a prediction presented as a measurement.

### 1.3 Method and reproduction

- Read every backend module listed in §3, every frontend page, both API layers, the schemas, the seeds, the tests and the requirements.
- Ran one read-only SQL session against the live `marketpulse` database (container `marketpulse-mysql`, host port 3307). No writes, no schema changes, no service starts.
- Checked the Python environment for the libraries the modules would need (import + version print).
- Grepped for schedulers, notification code, ML/export imports, campaign/report/alert models.
- No live external calls were made: eMAG scraping, Reddit, Google Trends and OpenRouter were not contacted. Their current live behaviour is UNVERIFIED.

The exact query used for the data facts:

```sql
SELECT 'products', COUNT(*) FROM marketpulse.products
UNION ALL SELECT 'reviews', COUNT(*) FROM marketpulse.reviews
UNION ALL SELECT 'price_history', COUNT(*) FROM marketpulse.price_history
UNION ALL SELECT 'brands', COUNT(DISTINCT brand) FROM marketpulse.products
UNION ALL SELECT 'categories', COUNT(DISTINCT category) FROM marketpulse.products
UNION ALL SELECT 'trend_metrics', COUNT(*) FROM marketpulse.trend_metrics
UNION ALL SELECT 'llm_cache', COUNT(*) FROM marketpulse.llm_cache;
```

Output (CONFIRMED):

```
products        10
reviews         48
price_history   40
brands          5
categories      5
trend_metrics   5
llm_cache       6
```

---

## 2. Measured findings

### 2.1 The dataset, measured (CONFIRMED)

#### 2.1.1 Per product

| id | name | brand | category | price (RON) | rating | reviews | price points | launch |
|---|---|---|---|---|---|---|---|---|
| 1 | Samsung Galaxy S25 | Samsung | Smartphone | 3999.99 | 4.00 | 7 | 4 | Feb 2025 |
| 2 | Apple iPhone 16 | Apple | Smartphone | 4499.99 | 4.14 | 7 | 4 | Sep 2024 |
| 3 | Sony WH-1000XM5 | Sony | Headphones | 1499.99 | 4.67 | 6 | 4 | May 2022 |
| 4 | NVIDIA GeForce RTX 5080 | NVIDIA | Graphics Card | 5999.99 | 4.20 | 5 | 4 | Jan 2025 |
| 5 | Apple MacBook Pro 14 M4 | Apple | Laptop | 8999.99 | 4.60 | 5 | 4 | Nov 2024 |
| 6 | Microsoft Surface Laptop 7 | Microsoft | Laptop | 5499.00 | 4.00 | 4 | 4 | Jun 2024 |
| 7 | Samsung Galaxy S25 Ultra | Samsung | Smartphone | 6499.99 | 4.20 | 5 | 4 | Feb 2025 |
| 8 | NVIDIA GeForce RTX 4070 Super | NVIDIA | Graphics Card | 3299.00 | 4.67 | 3 | 4 | Jan 2024 |
| 9 | Sony PlayStation 5 Slim | Sony | Gaming | 2799.00 | 4.33 | 3 | 4 | Nov 2023 |
| 10 | Microsoft Xbox Series X | Microsoft | Gaming | 2499.00 | 4.33 | 3 | 4 | Nov 2020 |

CONFIRMED by the read-only query above. Two consequences that shape every module:

- **`product.rating` is the average of the 3–7 stored reviews, not the retailer's rating.** `seeds.py:441-450` recalculates `product.rating` from stored reviews; `data_collection/reviews.py:154-169` does the same after every collection. The seeded `PRODUCTS` values (e.g. 4.6 for the Galaxy S25, `seeds.py:38`) are overwritten by the review average (4.00 in the DB).
- **`product.review_count` is the number of stored reviews, not the market review count.** `seeds.py:446` and `reviews.py:166` set it to the stored count. The eMAG connector can capture a market count on import (`api/products.py:398`, `connectors/emag.py:93-95`), but the seed and the collector overwrite it.

#### 2.1.2 Reviews

| Dimension | Value |
|---|---|
| Total reviews | 48 |
| Distinct authors | **48** (zero repeat authors) |
| Sources | eMAG 22, Reddit 16, TechCommunity 10 |
| Sentiment labels | positive 30, neutral 16, negative **2** |
| Reviews with non-empty `aspects` | 36 / 48 |
| Date range | 2026-09-10 → 2026-11-06 (57 days) |
| Ratings | 3★ 6, 4★ 22, 5★ 20 (no 1★ or 2★) |
| Reviews per brand | Apple 12, Samsung 12, Sony 9, NVIDIA 8, Microsoft 7 |
| Reviews per product | 3–7 |

Aspect sentiment counts across all 48 reviews (CONFIRMED):

| Aspect | positive | neutral | negative | total |
|---|---|---|---|---|
| performance | 9 | 4 | 1 | 14 |
| price_value | 4 | 5 | 2 | 11 |
| battery | 5 | 3 | 2 | 10 |
| display | 8 | 0 | 1 | 9 |
| camera | 3 | 5 | 0 | 8 |
| software | 4 | 2 | 1 | 7 |
| build_quality | 4 | 0 | 0 | 4 |
| audio | 2 | 1 | 0 | 3 |

**There are 7 negative aspect mentions in the entire dataset.** The largest is 2 (battery, price_value). Any "recurring problem" claim must say "2 mentions", not "customers complain that…".

#### 2.1.3 Price history

- 4 points per product, 40 total, spanning 2026-09-08 → 2026-11-06 (59 days).
- The points are a deterministic seeded decline from a starting premium to the current price (`seeds.py:384-407`). The total range per product is 4.2 %–14 %.
- **There is no anomaly in the current data.** Every series is monotonic or near-monotonic downward. An anomaly detector run on this data would either find nothing or flag normal seeded movement.
- **There is one retailer.** `price_history` has no `retailer` column (`models.py:62-74`); `price_collector` searches eMAG only (`data_collection/prices.py:29`). "Comparații între comercianți" is impossible today.

#### 2.1.4 Trend metrics

- 5 rows, one per category: Smartphone, Laptop, Headphones, Graphics Card, Gaming.
- Values are **seeded constants** (`seeds.py:342-348`), not measured: e.g. Smartphone "AI smartphones" 88.5 / 92.0.
- `trend_collector.refresh_trends` **upserts** per `(category, keyword)` (`data_collection/trends.py:47-58`), so only the latest snapshot survives. There is no trend history to plot.
- `google_trends_connector.get_interest` returns one snapshot from a 3-month pytrends window (`connectors/google_trends.py:34-83`) and returns `[]` when unavailable — no fabricated fallback.

#### 2.1.5 Products per category

| Category | Products |
|---|---|
| Smartphone | 3 |
| Laptop | 2 |
| Graphics Card | 2 |
| Gaming | 2 |
| Headphones | 1 |

Any within-category normalization (price index, competitiveness score) is computed over 1–3 products. With one product, min = max and a min–max score is undefined; with two, the score is 0 or 100. This is a structural limit, not a bug.

### 2.2 What exists in code (CONFIRMED)

| Capability | Where it lives | What it actually does |
|---|---|---|
| Product schema | `backend/database/models.py:18-59` | name, brand, category, price, currency, source, source_url, sku (unique), rating, review_count, specs JSON, launch text |
| Price history schema | `models.py:62-74` | product_id, price, currency, recorded_at |
| Review schema | `models.py:77-103` | source, external_id, author, rating, title, content, sentiment_score, sentiment_label, aspects JSON, helpful, published_at |
| Trend schema | `models.py:106-119` | category, keyword, trend_score, search_interest, trend_direction, source, recorded_at |
| LLM cache | `models.py:122-138` | cache_key, model, prompt, response, expires_at |
| Sentiment + ABSA | `backend/services/sentiment_analysis.py:16-122` | VADER + tech lexicon; 8 aspects with regex patterns; per-aspect sentiment/score/mentions |
| Aspect aggregation | `backend/services/analytics_service.py:141-167` | positive/neutral/negative/total/score per aspect |
| Pros/cons phrases | `analytics_service.py:169-187` | "Battery life praised in N reviews" / "criticised in N reviews" |
| Brand statistics | `analytics_service.py:204-269` | SOV = brand reviews / all reviews; sentiment; health = 0.6 × sentiment + 0.4 × rating; topics/concerns |
| Weekly brand volume | `analytics_service.py:271-314` | 12 weekly buckets, indexed to the busiest week |
| Keyword cloud | `analytics_service.py:316-350` | term frequency, sentiment-weighted, stopword-filtered |
| Global sentiment trend | `analytics_service.py:352-386` | weekly positive/neutral/negative percentages |
| Consumer segments | `analytics_service.py:406-485` | 5 hardcoded segments assigned by aspect key, price-median fallback |
| Competitor dashboard | `analytics_service.py:491-568` | brand shares, price vs category median, feature matrix, recent activity |
| Marketing trends | `analytics_service.py:574-614` | weekly mentions per brand and source, indexed to 100 |
| Source volume | `analytics_service.py:616-623` | review count per source |
| Recommendations | `analytics_service.py:629-780` | price gap, sentiment strength, weak aspect, segment, brand leader |
| Overview | `analytics_service.py:786-891` | KPIs, evolution, mentions, top movers |
| Price stats | `backend/services/forecasting.py:14-55` | min/max/avg/change/history_points |
| Linear forecast | `forecasting.py:57-105` | least-squares projection |
| Rule-based product advice | `backend/services/recommendations.py:14-96` | buy/wait/value rules |
| LLM summaries | `backend/services/llm_service.py:170-338` | review summary, executive summary, marketing opportunities, cached |
| Price collection | `backend/data_collection/prices.py:21-94` | eMAG search by product name; appends a point on change; `sync_all_products` exists but is not routed |
| Review collection | `backend/data_collection/reviews.py:67-169` | eMAG/Reddit/HN/X, dedupe, VADER, aggregates |
| Trend collection | `backend/data_collection/trends.py:26-80` | 4 hardcoded topics, upsert |
| eMAG connector | `backend/connectors/emag.py:28-230` | search HTML, product reviews, price parser, brand inference |
| Reddit connector | `backend/connectors/reddit.py:107-213` | OAuth first, public fallback, `last_status` |
| Google Trends | `backend/connectors/google_trends.py:34-83` | pytrends snapshot; empty when unavailable |
| HN connector | `backend/connectors/alternative_reviews.py:25-84` | Algolia search |
| X connector | `backend/connectors/twitter.py:24-85` | bearer token only; returns `[]` without one |

### 2.3 What does not exist (CONFIRMED by grep and by reading)

- **No campaign model, table, endpoint or page.** `grep -rn "campaign" backend --include=*.py` finds only the assistant intent (`assistant.py:27-28`) and a CLI mention (`marketing_advisor.py:5`).
- **No report model, generation endpoint, export code or download route.**
- **No alert model, notification code or scheduler.** `grep` for `APScheduler|schedule|cron|BackgroundScheduler` finds only prose in `assistant.py:29` and `llm_service.py:186`.
- **No ML imports.** `grep` for `sklearn|numpy|pandas|scipy` in `backend/` finds nothing.
- **No export imports.** `grep` for `reportlab|pptx|openpyxl|matplotlib` in `backend/` finds nothing.
- **No customer table, customer_id, purchase history, demographics or repeat-author linkage.** 48 reviews have 48 distinct authors.
- **No retailer/merchant column** on `price_history`.
- **No discount/original-price column** anywhere.
- **No launch date** — `launch` is a free-text label (`models.py:34`); `created_at` is the DB insert time (`models.py:36`), which for the seed is the seed run.
- **No per-brand sentiment-over-time series.** `sentiment_trend` is global (`analytics_service.py:352-386`); `evolution_series` is volume, not sentiment.
- **No product-level or brand-level radar chart** — the only radar is the product comparison in `ProductAnalysis.jsx:214-233`.
- **No "scan all products" route.** `price_collector.sync_all_products` (`prices.py:85-94`) has no caller in `api/`.
- **No bulk import, CSV import, audit log, soft delete or optimistic concurrency.**

### 2.4 Libraries and packaging (CONFIRMED)

| Library | Installed globally | In `requirements.txt` | Used today |
|---|---|---|---|
| scikit-learn 1.9.0 | yes | no | no |
| numpy 2.4.2 | yes | no | no |
| pandas 3.0.1 | yes | no | no |
| scipy 1.17.1 | yes | no | no |
| reportlab 4.4.10 | yes | no | no |
| python-pptx 1.0.2 | yes | no | no |
| openpyxl 3.1.5 | yes | no | no |
| matplotlib 3.10.8 | yes | no | no |
| statsmodels | no | no | no |
| textblob / spacy / nltk | no | no | no |

`requirements.txt:30-38` says explicitly:

```
# - pandas / numpy / scikit-learn were removed: nothing imports them.
# - praw / textblob were removed: nothing imports them.
```

So the libraries are present on this machine but **not reproducible on a teammate's cold setup**. Adding any of them is a deliberate reversal of a prior cleanup and needs the user's approval (question 2).

There is **no virtual environment** in the repo: `backend/.venv`, `backend/venv`, `.venv` and `venv` do not exist. The app runs on global Python 3.13.7.

The frontend has no export library (`package.json:11-17`: lucide-react, react, react-dom, react-router-dom, recharts). Export should be backend-generated so there is one implementation and the browser does not need a second dependency tree.

### 2.5 Product CRUD: what exists and what is missing (CONFIRMED)

Backend routes, all in `backend/api/products.py`:

| Method | Path | Line | Notes |
|---|---|---|---|
| GET | `/api/products/` | 115 | search, category, brand, min_price, max_price, skip, limit |
| GET | `/api/products/compare` | 178 | 2–4 ids |
| GET | `/api/products/{id}` | 222 | card + history + forecast + reviews + LLM summary |
| GET | `/api/products/{id}/detail` | 322 | legacy raw ORM |
| POST | `/api/products/` | 337 | creates product + initial price point |
| POST | `/api/products/import-from-emag` | 361 | live eMAG search, imports the best match |
| PUT | `/api/products/{id}` | 417 | updates fields; appends a price point if the price changes |
| DELETE | `/api/products/{id}` | 452 | hard delete, cascades reviews and prices |
| GET | `/api/products/{id}/prices` | 468 | price history |
| GET | `/api/products/{id}/reviews` | 482 | review list |
| POST | `/api/products/{id}/collect-reviews` | 496 | live collection |
| POST | `/api/products/{id}/sync-price` | 523 | live eMAG price sync |

Backend gaps:

1. **`launch` cannot be created or edited.** `ProductCreate` (`schemas/product.py:8-21`) and `ProductUpdate` (`24-33`) do not include `launch`; `ProductResponse` (`36-43`) does not return it. The list/detail DTO `ProductCard` does include it (`schemas/dto.py:34`), so the field exists in one contract and not the other.
2. **Duplicate SKU is a 500, not a 409.** `sku` is unique (`models.py:29`); `create_product` (`api/products.py:337-358`) does not pre-check it, so a duplicate raises an unhandled `IntegrityError`.
3. **No review CRUD.** Reviews can only arrive through collection; there is no create/update/delete endpoint.
4. **No manual price-point CRUD.** A point is created only by product create, product update with a changed price, or collection.
5. **No bulk import.** One product per request; `import-from-emag` imports exactly one best match (`api/products.py:386-399`).
6. **No optimistic concurrency.** `updated_at` exists (`models.py:37-42`) but is not used as an ETag or `If-Match`.
7. **No soft delete or audit trail.** `DELETE` is a hard cascade (`api/products.py:452-465`).

Frontend gaps:

- `src/services/api.js` exports **only GET functions** for products: `getProducts` (74), `getProductComparison` (80), `getProductDetail` (86). There is no create/update/delete/import function anywhere in the file (read in full, 1-181).
- `ProductAnalysis.jsx` (read in full, 1-353) has search, category filter, sort, compare selection and a detail drawer — **no add, edit, delete or import control**.
- `getProducts` sends only `search` and `brand` (`api.js:74-78`), not `category`, `min_price` or `max_price`, although the backend supports them (`api/products.py:142-152`).
- There is no form component, no confirmation dialog for delete, and no success/error feedback for mutations.

**Verdict:** the CRUD backend is ~90 % there; the UI is 0 %. This is the highest-value, lowest-risk first PR.

### 2.6 Data-quality limits that decide feasibility (CONFIRMED)

These are the facts that must drive the module verdicts:

1. **48 reviews, 48 distinct authors.** No repeat customer, no purchase frequency, no cross-product customer journey. True customer segmentation is impossible without inventing customers.
2. **2 negative reviews, 7 negative aspect mentions.** "Recurring problems" can be listed, but the largest count is 2. It cannot be called recurring at scale.
3. **Ratings are 3/4/5 only.** No 1★/2★, so dissatisfaction analysis is structurally truncated.
4. **4 price points per product, 59 days, smooth seeded decline.** No anomaly exists; Isolation Forest has nothing to learn from.
5. **One retailer (eMAG).** No merchant comparison.
6. **5 trend rows, one snapshot each, seeded constants.** No interest history.
7. **1–3 products per category.** Within-category normalization is unstable.
8. **`launch` is text, not a date.** "Newly launched" cannot be computed reliably.
9. **`specs` keys are heterogeneous per category.** Smartphone uses Display/Processor/Memory/Storage/Battery/Camera; Laptop uses Processor/Display/Memory/Storage/Battery; Graphics Card uses Memory/Architecture/Interface/Power; Gaming uses Storage/Resolution/Drive/Features; Headphones uses Type/Noise cancelling/Battery/Connectivity/Weight (`seeds.py:28-216`). Cross-category spec comparison is meaningless; within-category it is 2–3 products.
10. **The sample is the market.** Every share (SOV, interest, segment size) is a share of the 48 stored reviews, not of the market. The UI must say so.

---

## 3. Every module the change would touch (file:line, each read)

The matrix first, then the detail.

| # | Module | Verdict with today's data | Effort | Key blocker |
|---|---|---|---|---|
| 1 | Product Radar | PARTIAL | M | no launch dates, no discounts, no competitor offers |
| 2 | Review Mining (ABSA) | PARTIAL (ABSA table real) | S/M | only 7 negative aspect mentions; reasons not extracted |
| 3 | Competitor Benchmarking | PARTIAL | S/M | no innovation/popularity data; 7–12 reviews per brand |
| 4 | Trend Discovery | PARTIAL | M | no trend history; 5 static rows |
| 5 | Marketing Campaign Lab | NEEDS DATA | M/L | no campaign history; simulator only assumption-driven |
| 6 | Customer Segmentation | PARTIAL as review-level ML; BLOCKED as customer segmentation | M | 48 authors, no customer identity |
| 7 | Price Intelligence | PARTIAL | S/M | 4 points, 1 retailer, no anomalies |
| 8 | Brand Health Monitor | FULL/PARTIAL | S/M | missing per-brand sentiment trend and SOV caveat |
| 9 | Market Opportunity Finder | PARTIAL | M | thin demand/competition/dissatisfaction components |
| 10 | Automated Business Reports | FULL on demand | M/L | scheduling needs a runner |
| 11 | Competitor Alerts | PARTIAL | S/M | no scheduler/notifications for true alerts |
| 12 | Product Lifecycle Tracker | NEEDS DATA | M | no launch date |
| 13 | Customer Satisfaction Index | FULL | S | formula is a product decision |
| 14 | Review Authenticity Signals | PARTIAL | S/M | heuristics only; no verdicts |
| 15 | Marketing Budget Optimizer | NEEDS DATA | M | no channel performance data |
| 16 | Keyword Intelligence | FULL (exists) | S | extend to n-grams/per-brand |
| 17 | Product Recommendation Engine | PARTIAL | M | content-based only; no user-item matrix |
| 18 | Executive Dashboard | FULL | S/M | composition of existing views |
| 19 | Product CRUD from UI | FULL backend; 0 % UI | S/M | no frontend mutation layer |

Effort scale: **S** = one focused PR, no schema change; **M** = one PR with a schema addition or a new page; **L** = multiple PRs or new data collection.

---

### 3.1 Product Radar

**Exists (CONFIRMED):**

- Product catalogue with price, rating, review_count, specs JSON, launch text, source, source_url, sku: `models.py:18-59`.
- Price history: `models.py:62-74`.
- Price collection from eMAG by product name: `data_collection/prices.py:21-83`; a point is appended only when the price changes (`prices.py:49-69`).
- Sync one product: `POST /api/products/{id}/sync-price` (`api/products.py:523-535`).
- Sync all products exists but is unreachable: `prices.py:85-94`; no route calls it.
- Import one product from eMAG: `POST /api/products/import-from-emag` (`api/products.py:361-414`).
- Spec comparison: `GET /api/products/compare` (`api/products.py:178-219`); UI renders spec rows (`ProductAnalysis.jsx:194-211`).
- Price change from the oldest point: `analytics_service.py:120-130`.
- Min/max/avg/change: `forecasting.py:14-55`.
- Mention intensity: `analytics_service.py:132-139`.
- Top movers: `analytics_service.py:862-882`; UI `MarketOverview.jsx:122-151`.

**Missing (CONFIRMED):**

- No scheduled monitoring: no scheduler anywhere (§2.3).
- No "scan all" endpoint.
- No new-launch detection: `launch` is text (`models.py:34`); no `launched_at` date; `created_at` is the DB insert time (`models.py:36`).
- No discount/original price: `price_history` has only price/currency/recorded_at (`models.py:65-69`).
- No rating history: `product.rating` is one current value (`models.py:30`); reviews have `published_at` (`models.py:93`), so a rating-over-time series is derivable per product, but from 3–7 points.
- No competitor-offer entity: brands are strings on products; no retailer/competitor table.
- No Product Competitiveness Score.

**Data present:** 10 products, 4 price points each, ratings 4.00–4.67, specs per category, 3–7 reviews each.

**Data missing:** launch dates, discount fields, multiple retailers, competitor offer snapshots, enough products per category for stable normalization.

**DB additions (additive only):**

- `products.launched_at` DATE NULL — the real launch date, distinct from the text label.
- `price_history.original_price` FLOAT NULL and `price_history.discount_pct` FLOAT NULL — a reduction is `original_price > price`; NULL means "not reported".
- `price_history.retailer` VARCHAR(100) NULL — the merchant; NULL means "unknown", not "eMAG".
- Optional: `product_events` table (id, product_id, event_type, payload JSON, observed_at) for "new product seen", "price drop", "rating change". This is the honest basis for alerts and a change feed.

**Libraries:** none for the score; scikit-learn only if a learned score is wanted (not recommended — the weights should be explicit).

**Effort:** M for the score + scan-all + change feed; L for real monitoring with a scheduler, launch dates and multi-retailer collection.

**Verdict:** **PARTIAL.** Price monitoring, rating display, spec comparison and a Competitiveness Score can be 100 % real now. "New launches", "discounts" and "competitor offer changes" need the new fields and repeated collection; without them the module must say "not tracked".

**Proposed Competitiveness Score (transparent, configurable):**

```
price_score    = 100 * (1 - (price - category_min) / (category_max - category_min))   # within category
spec_score     = 100 * (filled_specs / comparable_spec_keys)                          # completeness
rating_score   = rating / 5 * 100
sentiment_score= product_sentiment(reviews)                                           # 0-100 or None
score          = weighted mean of available components, weights renormalized to 1
```

Default weights: price 0.35, specs 0.25, rating 0.20, sentiment 0.20. If a component is `None`, drop it and renormalize; return `coverage` = available/total. With 1 product in a category, `price_score` is `null` (min = max); with 2, it is 0 or 100 — the UI must show the raw price and the category size.

---

### 3.2 Review Mining (ABSA)

**Exists (CONFIRMED):**

- VADER + 20-term tech lexicon: `sentiment_analysis.py:16-41`.
- `analyze_text` returns score/label/pos/neu/neg/aspects: `sentiment_analysis.py:55-90`.
- 8 aspect patterns: battery, camera, display, performance, price_value, build_quality, software, audio (`sentiment_analysis.py:44-53`).
- Per-aspect extraction with sentence-level sentiment and mention count: `sentiment_analysis.py:92-122`.
- Per-review aspects stored as JSON: `models.py:90`; populated at collection (`reviews.py:122-135`) and at seed (`seeds.py:423-436`).
- Aggregation to positive/neutral/negative/total/score: `analytics_service.py:141-167`.
- Pros/cons phrases: `analytics_service.py:169-187`.
- API: `GET /api/analytics/sentiment` returns `aspects` (`api/analytics.py:83-91`).
- UI: aspect bar chart (`SentimentAnalysis.jsx:117-134`); pros/cons in the drawer (`ProductAnalysis.jsx:305-318`).
- Keyword cloud: `analytics_service.py:316-350`; UI `SentimentAnalysis.jsx:136-155`.

**Missing (CONFIRMED):**

- **Reasons are not extracted.** Pros/cons are counts, not the reason text: "Battery life praised in 5 reviews" (`analytics_service.py:177-186`). The aspect sentence that produced the sentiment is not stored, although it is recomputable from `review.content`.
- **No recurring-problem phrase mining.** No n-gram extraction, no phrase clustering, no "battery drains fast" / "overheats" list. The lexicon contains `drain`, `battery drain`, `overheating` (`sentiment_analysis.py:19-40`), but nothing aggregates them into problems.
- **No "mixed" label in the UI.** `aspect_breakdown` stores positive/neutral/negative counts and a score (`analytics_service.py:146-166`); the API returns only `score` and `mentions` (`api/analytics.py:84-91`), so "mixed" is not visible.
- **No aspect table per product with reasons.** The sentiment page shows a global aspect bar chart; the drawer shows pros/cons for one product, not a feature → sentiment table with counts and example sentences.
- **No aspect editing/verification.**
- **No LLM-based ABSA.** Only VADER; an LLM extraction would cost the free-tier budget and is not needed for the 8 fixed aspects.

**Data present:** 48 reviews, 36 with aspects, 8 aspects, 7 negative aspect mentions.

**Data missing:** enough negative mentions for "recurring"; the reason sentences are present in `content` but not surfaced.

**DB additions:** none strictly required. Optional additive `reviews.aspect_sentences` JSON (aspect → list of matching sentences) to avoid recomputation and to make reasons auditable. If added, backfill in a one-off script; NULL means "not extracted".

**Libraries:** none. Standard library `re` and `collections` suffice. An LLM pass is optional and must be cached.

**Effort:** S/M for the feature → sentiment table with reasons and counts; M for phrase mining (n-grams + stopwords + aspect association).

**Verdict:** **PARTIAL.** The ABSA table requested by the user (feature → sentiment) is 100 % real today and is the strongest differentiator. "Recurring problems" can be listed with exact counts, but the largest count is 2; the UI must say "2 mentions in 48 reviews", never "customers complain". Reasons can be extracted from the stored `content` without new data.

---

### 3.3 Competitor Benchmarking

**Exists (CONFIRMED):**

- Brand stats: SOV, mentions, sentiment, health, topics, concerns (`analytics_service.py:204-269`).
- Health formula: 0.6 × sentiment + 0.4 × (rating / 5 × 100) (`analytics_service.py:239-243`); if rating is missing, health = sentiment (`242-243`).
- Price positioning vs category median: `analytics_service.py:502-522`.
- Feature matrix per brand: `analytics_service.py:526-541`.
- Recent activity: `analytics_service.py:543-560`.
- API: `GET /api/analytics/competitors` (`api/analytics.py:147-153`).
- UI: Competitive Positioning Map — average price vs perceived quality (health), bubble size = share (`CompetitorAnalysis.jsx:23-34`, chart `50-84`).
- Price difference bar chart (`CompetitorAnalysis.jsx:86-106`).
- Feature matrix (`CompetitorAnalysis.jsx:109-144`).
- Brand multi-select for chart lines (`BrandIntelligence.jsx:55-70`).
- Product radar for 2–4 products (`ProductAnalysis.jsx:214-233`).

**Missing (CONFIRMED):**

- **No brand-level radar chart.** The only radar is product-level (`ProductAnalysis.jsx:214-233`).
- **No explicit 2+ company comparator.** The UI shows all brands and filters by one global brand; there is no "select Apple and Samsung, compare on 7 dimensions" control.
- **No Customer Satisfaction Index.** Sentiment is the proxy.
- **No innovation indicators.** No launch dates, no feature recency, no R&D proxy.
- **No online popularity beyond stored review counts.** No followers, search volume or social reach.
- **No per-brand rating distribution.** Only the average.
- **No sample-size warning.** Apple 12, Samsung 12, Sony 9, NVIDIA 8, Microsoft 7 reviews; a 7-review average is not a market rating.
- **`product.rating` is the stored-review average, not the retailer rating** (§2.1.1).

**Data present:** 5 brands, 7–12 reviews each, 1–2 products each, ratings, price, aspects.

**Data missing:** innovation signals, true popularity, larger samples.

**DB additions:** none for the existing dimensions. For innovation: `products.launched_at` (shared with Product Radar) and optionally `products.spec_generation` / a `product_features` table. For popularity: a `brand_metrics` table (brand, metric, value, source, recorded_at) fed by connectors — a new data source, not a schema-only change.

**Libraries:** none. The radar is a Recharts component already available (`recharts` in `package.json:16`).

**Effort:** S/M for the brand radar, 2+ selector, CSI, sample-size warnings; L for innovation/popularity data.

**Verdict:** **PARTIAL.** Brand sentiment, ratings, price positioning, satisfaction proxy, review volume and the positioning map are 100 % real now. Innovation and true online popularity need new data; they must be shown as "not tracked" rather than approximated.

---

### 3.4 Trend Discovery

**Exists (CONFIRMED):**

- `trend_metrics` table: `models.py:106-119`.
- Collector with 4 hardcoded topics: `data_collection/trends.py:19-24`; upsert: `26-80`.
- Google Trends connector: one snapshot from a 3-month window (`connectors/google_trends.py:34-83`); empty on failure, no fabrication (`78-83`).
- API `GET /api/analytics/trends` (`api/analytics.py:357-424`): returns recorded trends if any, else derives a score from product and review counts (`389-424`).
- `POST /api/analytics/refresh-trends` (`api/analytics.py:455-461`).
- Weekly mention volume per brand/source: `analytics_service.py:574-614`.
- Weekly review volume per brand: `analytics_service.py:271-314`.
- UI: marketing trends (`MarketingAnalytics.jsx:54-87`), brand evolution (`BrandIntelligence.jsx:98-118`), market evolution (`MarketOverview.jsx:71-92`).

**Missing (CONFIRMED):**

- **No trend history.** The collector upserts per `(category, keyword)` (`trends.py:47-58`), so only the latest snapshot exists. "Evoluția interesului" cannot be computed.
- **The 5 seeded trend rows are constants** (`seeds.py:342-348`), not measurements.
- **No Trend Momentum Score.**
- **Only 4 tracked topics** (`trends.py:19-24`), not products/brands/categories generally.
- **No search-evolution series.**
- **The only real time series is review volume:** 9 weeks, 1–7 reviews/week.
- **`refresh-trends` is a live external call** and may fail or rate-limit; with no history, a failure leaves stale values.

**Data present:** 9 weeks of reviews, 5 static trend rows, 4 topics.

**Data missing:** trend time series, search history, enough volume for stable growth rates.

**DB additions:**

- `trend_metrics` is already append-shaped except for the upsert; change the writer to **insert a new row per refresh** instead of updating, and add an index on `(keyword, recorded_at)`. This is additive in behaviour but changes row volume; existing readers that take the latest row per keyword must be updated.
- Optional `trend_topics` table (keyword, entity_type, entity_id, active) to track products/brands, not just 4 hardcoded topics.

**Libraries:** `pytrends` is already in `requirements.txt:22`. No new library.

**Effort:** M for history + momentum + UI; L for broad topic coverage and reliable search data.

**Proposed Trend Momentum Score (transparent, coverage-aware):**

```
mention_growth = (mentions_last_4w - mentions_prev_4w) / max(mentions_prev_4w, 1) * 100
review_growth  = same, on review count
rating_change  = avg_rating_last_4w - avg_rating_prev_4w          # points, -5..+5
search_change  = (latest_interest - earliest_interest) / earliest * 100   # only if >= 2 history rows
momentum       = weighted mean of available components, weights renormalized
```

Default weights: mention 0.35, review 0.35, rating 0.15, search 0.15. Return every component with its raw value, sample size and source; return `null` for search when there is no history. If either 4-week window has fewer than 10 reviews, label "low confidence". Never present the score as a forecast.

**Verdict:** **PARTIAL.** A transparent momentum score can be built now from review volume and rating change. The search component must be `null` / "not measured" until trend history exists. The seeded 5 rows must not be used as if they were history.

---

### 3.5 Marketing Campaign Lab

**Exists (CONFIRMED):**

- Nothing structured. The assistant has a "campaign" intent that writes prose (`assistant.py:27-28`); `marketing_advisor.py` is a CLI.
- Marketing context: `marketing_trends` (`analytics_service.py:574-614`) and `_derived_opportunities` (`api/marketing.py:23-82`).
- No campaign model, endpoint, page, result or history.

**Missing (CONFIRMED):**

- Campaign entity: objective, target segment, channels, budget, KPIs, variants, dates, status.
- Campaign results: spend, impressions, clicks, conversions, revenue.
- Simulator: assumptions and formulas.
- Historical campaign data to calibrate any estimate.

**Data present:** none for campaigns.

**Data missing:** all campaign data.

**DB additions (proposed):**

- `campaigns` (id, name, objective, target_segment, channels JSON, budget, currency, starts_at, ends_at, status, created_at, updated_at).
- `campaign_variants` (id, campaign_id, name, channel_mix JSON, budget, assumptions JSON, kpis JSON).
- `campaign_results` (id, variant_id, recorded_at, spend, impressions, clicks, conversions, revenue, source).
- All additive; no existing table changes.

**Libraries:** none for CRUD. For simulation, plain arithmetic. If a Monte Carlo range is wanted, numpy is already installed; it is optional and must be labelled as a scenario, not a prediction.

**Effort:** M/L — tables + CRUD + UI + simulator.

**Verdict:** **NEEDS DATA** for the "evaluare rezultate" half. The **Campaign Simulator can be 100 % real as an assumption calculator**: the user enters budget, channel mix, assumed CPM/CPC/CTR/CVR/AOV; the app computes impressions, clicks, conversions, revenue, ROAS and CAC, and shows every formula. It must not claim to predict outcomes. If historical results are later imported, the same simulator can show observed vs assumed side by side.

---

### 3.6 Customer Segmentation

**Exists (CONFIRMED):**

- `consumer_segments` (`analytics_service.py:406-485`): 5 hardcoded definitions (`421-427`), assignment by aspect key (`429-444`), aggregates size/spend/loyalty/sensitivity (`446-484`).
- API `GET /api/analytics/consumer-segments` (`api/analytics.py:139-144`).
- UI: segment cards, purchase drivers, sensitivity vs loyalty scatter (`ConsumerInsights.jsx:44-111`).

**Missing (CONFIRMED):**

- **No ML.** No sklearn, no clustering, no PCA (§2.3).
- **No customer identity.** 48 reviews, 48 distinct authors; no `customer_id`, no purchase frequency, no demographics.
- **No brand preference per customer.** Each review is about one product.
- **No technology preference per customer** beyond the aspect of one review.
- **No ratings-offered history per customer.**
- **No feature-interest vector** beyond aspect presence.

**Data present:** 48 review-level rows with 8 aspects, rating, product price, brand, source, helpful, text length.

**Data missing:** repeat customers, purchase history, demographics.

**DB additions:** none for review-level ML. For true customer segmentation: a `customers` table and a `customer_id` on reviews, plus repeated observations — a new data source, not a schema tweak.

**Libraries:** scikit-learn (KMeans, AgglomerativeClustering, DBSCAN, PCA, StandardScaler, silhouette_score), numpy, pandas. All installed, none declared.

**Effort:** M for the review-level ML; L for true customer segmentation.

**Proposed approach (honest):**

- Feature matrix per review: 8 aspect sentiment scores (−1..1) or presence, rating (1–5), product price (normalized within category), brand one-hot (5), source one-hot (3), helpful (normalized), review length.
- StandardScaler → KMeans(k=3..6), choose k by silhouette; Agglomerative (Ward) for a dendrogram; DBSCAN with tuned eps (likely noise); PCA 2D for the scatter.
- Output: cluster sizes, mean feature profile, silhouette, PCA coordinates, a human label derived from the dominant feature ("price-sensitive", "performance-focused", "display-focused").
- **Caveat in the API and the UI:** "Segments of 48 reviews by 48 distinct authors; exploratory, not customer segments."
- If n < 30 or fewer than 3 features → return `{"status": "not_enough_data", "n": 48}`.

**Verdict:** **PARTIAL as review-level ML; BLOCKED as customer segmentation.** The user's dimensions (purchase frequency, brand preference, ratings offered) require a customer identity that does not exist. The honest build is "audience segments derived from reviews", with the ML shown as exploratory and its quality metric visible.

---

### 3.7 Price Intelligence

**Exists (CONFIRMED):**

- Price history: `models.py:62-74`; 4 points per product, 59 days.
- Min/max/avg/change/history_points: `forecasting.py:14-55`.
- Change from the oldest point: `analytics_service.py:120-130`.
- API `GET /api/analytics/prices?product_id=` (`api/analytics.py:327-354`).
- API `GET /api/products/{id}/prices` (`api/products.py:468-479`).
- Product drawer price chart + linear forecast (`ProductAnalysis.jsx:270-294`; forecast built in `api/products.py:265-275`).
- Top movers (`analytics_service.py:862-882`; UI `MarketOverview.jsx:122-151`).

**Missing (CONFIRMED):**

- **No retailer dimension** (`models.py:65-69`); only eMAG is collected (`prices.py:29`).
- **No discount/original price** anywhere.
- **No anomaly detection.**
- **No price-vs-rating chart** (both fields exist; the UI does not show it).
- **No volatility metric** beyond min/max.
- **No forecast confidence or backtest.**

**Data present:** 4 points/product, 59 days, ranges 4.2–14 %, monotonic seeded decline.

**Data missing:** high-frequency snapshots, multiple retailers, actual discounts, anomalies.

**DB additions:** `price_history.retailer` VARCHAR(100) NULL; `price_history.original_price` FLOAT NULL; `price_history.discount_pct` FLOAT NULL. Optional `price_history.source` is already implicit in the product; the retailer is the missing dimension.

**Libraries:** none for statistical/rule-based detection. scikit-learn IsolationForest is available but **not meaningful on 4 points per product**; it needs a longer series.

**Effort:** S/M for fluctuations, consecutive-drop detection, price-vs-rating, rule-based anomaly; L for Isolation Forest with enough data.

**Verdict:** **PARTIAL.** History, fluctuations, percentage differences and price vs rating are 100 % real now. Multi-retailer comparison is **BLOCKED** by the missing retailer dimension. Anomaly detection must be rule-based (`drop > X % between consecutive points`) and will find nothing in the current smooth data; the UI must say "no anomaly detected" or "not enough points", never invent one.

---

### 3.8 Brand Health Monitor

**Exists (CONFIRMED):**

- Brand stats: SOV, mentions, sentiment, health, topics, concerns (`analytics_service.py:204-269`).
- SOV formula in code: `_pct(len(reviews), total_reviews)` (`analytics_service.py:260`); the denominator is all stored reviews (`219`).
- Weekly volume per brand: `analytics_service.py:271-314`.
- Global sentiment trend: `analytics_service.py:352-386`.
- Source volume: `analytics_service.py:616-623`.
- API `GET /api/analytics/brands` (`api/analytics.py:124-136`).
- UI: health banner (`BrandIntelligence.jsx:72-96`), evolution (`98-118`), SOV (`120-136`), topics/concerns (`139-176`), leader callout (`178-191`).
- Market overview SOV donut (`MarketOverview.jsx:94-119`).

**Missing (CONFIRMED):**

- **No per-brand sentiment-over-time series.** `sentiment_trend` is global; `evolution_series` is volume.
- **No positive/negative mention counts per brand** exposed (derivable from labels).
- **No explicit SOV caveat in the API or the UI.** The UI says "Across N stored reviews" (`BrandIntelligence.jsx:134`) but not "only monitored sources and period".
- **No net sentiment or sentiment volatility.**
- **No brand comparison radar.**

**Data present:** 5 brands, 7–12 reviews each, 9 weeks.

**Data missing:** larger samples, external share data.

**DB additions:** none. All derivations are computed from `reviews` and `products`.

**Libraries:** none.

**Effort:** S/M.

**Verdict:** **FULL/PARTIAL.** Almost everything requested is computable now: sentiment, SOV, positive/negative counts, themes, competitor comparison. Add the per-brand sentiment trend and the explicit caveat. State the formula in the UI: `SOV = brand mentions / all monitored mentions × 100`, and "only eMAG, Reddit and TechCommunity, 2026-09-10 → 2026-11-06".

---

### 3.9 Market Opportunity Finder

**Exists (CONFIRMED):**

- Recommendation rules: price gap (`analytics_service.py:660-692`), sentiment strength (`695-710`), weak aspect (`713-732`), segment (`735-752`), brand leader (`755-777`).
- Derived opportunity cards: `api/marketing.py:23-82`.
- API `GET /api/analytics/recommendations` (`api/analytics.py:168-275`).
- UI: AI Recommendations (`AIRecommendations.jsx:44-96`); marketing opportunities (`MarketingAnalytics.jsx:151-179`).

**Missing (CONFIRMED):**

- **No formal Market Opportunity Score.**
- **No demand estimate** beyond review volume.
- **No competition-intensity metric** (products/brands per category).
- **No dissatisfaction index** (only 7 negative aspect mentions).
- **No interest evolution** (trend history missing).
- **No component coverage/confidence display.**

**Data present:** price gaps, sentiment, aspects, segments, review volume.

**Data missing:** demand, competition, interest history, enough dissatisfaction.

**DB additions:** none for a computed score. If opportunities are saved/actioned, an `opportunities` table (id, title, category, score, components JSON, status, created_at) is additive.

**Libraries:** none.

**Effort:** M.

**Proposed Market Opportunity Score (coverage-aware):**

```
demand          = percentile of review volume within category (0-100)
competition     = 100 - percentile of product count within category (fewer products = less competition)
dissatisfaction = negative aspect share within category (0-100)
price_gap       = |price - category median| / median * 100, capped at 100
interest        = trend momentum (0-100) or null
score           = weighted mean of available components, weights renormalized
coverage        = available / 5
```

Default weights: demand 0.25, competition 0.20, dissatisfaction 0.25, price 0.15, interest 0.15. Return every component with its raw value and sample size. If coverage < 3/5, return `status: "low_coverage"` and do not show a single headline score. Never call it a probability.

**Verdict:** **PARTIAL.** A score can be computed, but with 2 negative reviews and 2–3 products per category the dissatisfaction and competition components are thin. The UI must show coverage and raw inputs; the module is a prioritization aid, not a success probability.

---

### 3.10 Automated Business Reports

**Exists (CONFIRMED):**

- All content sources: overview (`analytics_service.py:786-891`), brand stats (`204-269`), competitor dashboard (`491-568`), sentiment (`55-121` in `api/analytics.py`), recommendations (`629-780`).
- Optional LLM summary: `llm_service.py:308-338`.
- No report model, endpoint, template, export or download.

**Missing (CONFIRMED):**

- Report entity and generation endpoint.
- Section templates: Executive Summary, Market Overview, Product Performance, Competitor Analysis, Consumer Sentiment, Marketing Opportunities, Strategic Recommendations.
- Export: CSV, Excel, PDF, PowerPoint.
- Download route and file storage convention.
- Scheduling (weekly/monthly).

**Data present:** enough for a report on the current dataset.

**Data missing:** none for an on-demand report; scheduling needs a runner.

**DB additions:** `reports` (id, title, scope_type, scope_id, format, status, file_path, created_at, completed_at, error) — additive. Optional `report_schedules` (id, cron, scope, format, active) for the later scheduling PR.

**Libraries:** `csv` (stdlib) for CSV; `openpyxl` 3.1.5 for Excel; `reportlab` 4.4.10 for PDF; `python-pptx` 1.0.2 for PowerPoint; `matplotlib` 3.10.8 (Agg backend) for chart images. All installed, none declared.

**Effort:** M for CSV/Excel; L for PDF/PPTX with charts + background generation + download; scheduling is a separate PR.

**Verdict:** **FULL on demand.** Every section can be assembled from existing services. Export is feasible. Weekly/monthly scheduling needs a scheduler that does not exist; do it later or use the OS scheduler with a documented command.

---

### 3.11 Competitor Alerts

**Exists:** nothing.

**Missing:** alert rules, alert model, check job, notification channel, UI.

**Data present:** price history, products, reviews — enough to compute signals.

**Data missing:** a scheduler and a notification channel for true push alerts.

**DB additions:** `alerts` (id, type, entity_type, entity_id, severity, title, detail, payload JSON, created_at, read_at) — additive. A computed feed can be built without a table; a persisted alert needs one.

**Libraries:** none for the feed; APScheduler (not installed) or the OS scheduler for a job.

**Effort:** S/M for a computed "signals" feed; M/L for scheduled push.

**Verdict:** **PARTIAL.** A "what changed" feed (price drop > X %, new product, rating change, new negative aspect) can be computed on request now. Push notifications need a scheduler and a channel; do not claim them until they exist.

---

### 3.12 Product Lifecycle Tracker

**Exists:** `launch` text label (`models.py:34`); `created_at` (`models.py:36`); price history; review volume.

**Missing:** a real launch date; a lifecycle-stage definition; enough history.

**Data present:** text labels only ("Feb 2025", "Sep 2024", …).

**Data missing:** `launched_at` DATE, first-seen snapshots, market availability.

**DB additions:** `products.launched_at` DATE NULL (shared with Product Radar); optional `product_events` for stage transitions.

**Libraries:** none.

**Effort:** M.

**Verdict:** **NEEDS DATA.** A stage can be inferred from the text label + price trend + review volume, but the label is free text and the sample is 10 products. Build it only after `launched_at` exists; until then show "launch date not tracked".

---

### 3.13 Customer Satisfaction Index

**Exists:** sentiment (`analytics_service.py:100-118`), rating, aspect scores.

**Missing:** a documented composite formula and a UI surface.

**Data present:** enough to compute.

**DB additions:** none.

**Libraries:** none.

**Effort:** S.

**Proposed formula:**

```
CSI = 0.45 * sentiment_score + 0.35 * (rating / 5 * 100) + 0.20 * mean_aspect_score
```

Return `null` if any component is missing; show the components and the weights. With 3–7 reviews per product, label "based on N reviews".

**Verdict:** **FULL.**

---

### 3.14 Review Authenticity Signals

**Exists:** review text, author, rating, source, published_at, helpful.

**Missing:** any signal computation.

**Data present:** 48 reviews, 48 distinct authors, no duplicate text (the collector dedupes by content, `reviews.py:104-119`), ratings 3–5.

**Data missing:** a larger corpus for meaningful patterns; ground truth.

**DB additions:** optional `reviews.authenticity_signals` JSON (flags + reasons), additive.

**Libraries:** none required; token Jaccard/cosine is enough. scikit-learn optional.

**Effort:** S/M.

**Signals (transparent, no verdict):** very short text (< 40 chars), extreme rating with no aspect, near-duplicate text (Jaccard > 0.8), same author across products (none today), burst within 24 h (none today), generic marketing phrases. Output flags with reasons; never label a review "fake".

**Verdict:** **PARTIAL.** The signals can be computed, but with 48 reviews and no ground truth they are weak. Present them as "signals to review", not authenticity scores.

---

### 3.15 Marketing Budget Optimizer

**Exists:** segment sizes (`analytics_service.py:406-485`), aspect scores, marketing trends.

**Missing:** channel performance data, spend, conversions, CAC/ROAS history.

**Data present:** none for channel performance.

**Data missing:** all performance data.

**DB additions:** depends on Campaign Lab (`campaign_results`).

**Libraries:** none; linear allocation arithmetic.

**Effort:** M.

**Verdict:** **NEEDS DATA** for a data-driven optimizer. An allocation calculator from user assumptions + segment sizes is possible, but it must be labelled "scenario", not "optimization".

---

### 3.16 Keyword Intelligence

**Exists:** `keyword_cloud` (`analytics_service.py:316-350`), stopwords (`48-62`), UI (`SentimentAnalysis.jsx:136-155`).

**Missing:** n-grams, per-brand/per-aspect keywords, trend over time, keyword → product association.

**Data present:** 48 review texts.

**Data missing:** volume for stable keyword trends.

**DB additions:** none; compute on request.

**Libraries:** none.

**Effort:** S.

**Verdict:** **FULL** for the existing cloud and simple extensions (bigrams, per-brand, per-aspect). Trend over time is thin with 9 weeks.

---

### 3.17 Product Recommendation Engine

**Exists:** product specs, aspect scores, price, rating, brand.

**Missing:** any recommendation endpoint or UI.

**Data present:** 10 products, enough for content-based similarity.

**Data missing:** a user-item interaction matrix for collaborative filtering.

**DB additions:** none for content-based; optional `recommendation_feedback` for learning.

**Libraries:** none required; cosine similarity on normalized features is enough. scikit-learn optional.

**Effort:** M.

**Verdict:** **PARTIAL.** Content-based "similar products" and "better alternatives" (higher score, lower price) are 100 % real. Collaborative filtering is **BLOCKED** by the absence of user-item interactions.

---

### 3.18 Executive Dashboard

**Exists:** MarketOverview (`MarketOverview.jsx:17-188`), AIRecommendations (`AIRecommendations.jsx:10-107`), BrandIntelligence, CompetitorAnalysis.

**Missing:** a single aggregated executive view.

**Data present:** enough.

**DB additions:** none.

**Libraries:** none.

**Effort:** S/M.

**Verdict:** **FULL** as a composition of existing views: KPI row, top movers, brand leader, top opportunity, alerts/signals, latest mentions.

---

### 3.19 Product CRUD from UI

Covered in §2.5. Summary:

- Backend: create/update/delete/import exist (`api/products.py:337, 417, 452, 361`); `launch` is missing from the CRUD schemas (`schemas/product.py:8-43`); duplicate SKU is a 500; no review/price CRUD.
- Frontend: no mutation functions in `api.js` (read in full); no add/edit/delete UI in `ProductAnalysis.jsx` (read in full).
- **Effort:** S/M for full CRUD UI + field fixes; M for bulk import/audit.

**Verdict:** **FULL backend, 0 % UI.** This is the first PR.

---

## 4. Options, with evidence and the bytes each one changes

### 4.1 Option A — Data-first, honest modules (recommended)

Build only what the stored data supports; add schema fields only where they unlock a real capability; label every thin sample.

- **What ships:** CRUD UI; Review Mining table + reasons; Brand Health additions; Price Intelligence additions; Competitor Benchmarking additions; Product Radar score + change feed; Trend Momentum with null search; Opportunity Score with coverage; Reports on demand; CSI; Keyword Intelligence; Executive Dashboard.
- **What is deferred or labelled:** Campaign Lab (assumption calculator only), Customer Segmentation (review-level, exploratory), Anomaly Detection (rule-based, "no anomaly"), multi-retailer (not tracked), lifecycle (needs dates), push alerts (needs scheduler), scheduled reports (needs runner).
- **Change surface:** ~6–8 new backend modules, ~4 new frontend pages/sections, 3–4 additive columns, 2–3 new tables (`reports`, `campaigns`/variants/results, optional `alerts`). Existing response shapes stay unchanged where possible; new fields are additive and nullable.
- **Why:** it respects the product principles (no invented limits, no placeholder as product, unknown ≠ unsupported) and gives a demo where every number can be defended.

### 4.2 Option B — Breadth-first with assumption-driven outputs (rejected)

Build all 10 modules now, filling gaps with estimates.

- **What it would do:** fabricate campaign lift, invent trend history, claim anomaly detection on 4 points, call rule-based segments "ML", present a competitiveness score as a market measure.
- **Why it is rejected:** it violates `WORKING-NOTES` PART IV.9 ("no hand-entered facts where a source exists"), IV.19 ("no placeholder presented as product") and the user's own warning ("nu trebuie să prezinte estimările ca rezultate garantate"). The user verifies independently (PART I.4) and rejects placeholders (I.5).
- **Change surface:** the same files, but with numbers that cannot be traced to a row. Higher demo risk, not lower.

### 4.3 Option C — Collect more data first, then build everything

Invest in collection before analytics: daily price snapshots, multiple retailers, launch dates, trend history, campaign results, customer identity.

- **What it unlocks:** real anomaly detection, real trend momentum, real customer segmentation, real campaign evaluation, real multi-retailer comparison.
- **Cost:** collection time (days/weeks), new connectors, rate limits, a scheduler, a customer identity source that does not exist.
- **Why not first:** the hackathon demo needs visible value now; the data-real modules already deliver it. Option C is the right **second wave** for the modules that need it.

### 4.4 Per-module options

| Decision | Option 1 | Option 2 | Option 3 | Recommendation |
|---|---|---|---|---|
| Segmentation algorithm | K-Means (simple, needs k) | Hierarchical/Ward (dendrogram) | DBSCAN (finds noise, hard eps) | K-Means + PCA for the demo; show silhouette; Hierarchical as a second view; DBSCAN only as an experiment |
| Anomaly detection | Isolation Forest | Statistical (z-score / IQR) | Rule-based threshold | Rule-based now (4 points); statistical when ≥ 8 points; Isolation Forest only with ≥ 30 points per product |
| Export | Backend-generated | Frontend-generated | Both | Backend only (one implementation, no new frontend deps) |
| Report generation | Synchronous | Background task + download | Scheduled | Background task now; scheduled later |
| Competitiveness weights | Fixed defaults | User-configurable | Learned | Fixed defaults + a settings surface; never learned on 10 products |
| SOV denominator | All stored reviews | Category reviews | Market share | All stored reviews, with the explicit caveat; category variant as a filter |
| Trend momentum | Review volume only | + search history | + social volume | Review volume + rating change now; search null until history; social later |
| Customer segmentation | Review-level | Customer-level | Hybrid | Review-level, labelled "audience segments"; customer-level only with a customer table |

### 4.5 Change surface per option (estimated, not measured bytes)

| Option | New backend files | New frontend files | New tables/columns | Existing outputs |
|---|---|---|---|---|
| A | ~6–8 services/routers | ~4 pages/sections | 3–4 columns, 2–3 tables | unchanged; new fields additive and nullable |
| B | same | same | same | existing shapes may change if estimates replace nulls — rejected |
| C | connectors + jobs | same | many columns/tables | unchanged, but delivery delayed |

"Bytes" here means the change surface, not a byte count: no code was written, so no byte-level diff exists. The important equality property is that **existing endpoints keep their current response shapes**; every new field is additive and `null` when not measured.

---

## 5. Recommendation (precise)

### Wave 0 — CRUD (1 PR, S/M)

1. Add `launch` to `ProductCreate`, `ProductUpdate`, `ProductResponse` (`schemas/product.py:8-43`).
2. Pre-check duplicate SKU and return 409 (`api/products.py:337-358`).
3. Add `createProduct`, `updateProduct`, `deleteProduct`, `importFromEmag` to `src/services/api.js`.
4. Add an "Add product" form, an edit action in the drawer, a delete confirmation, and an eMAG import dialog to `ProductAnalysis.jsx`.
5. Pass `category`, `min_price`, `max_price` from `getProducts` (`api.js:74-78`).
6. Tests: contract tests for the four mutations; Playwright for create → edit → delete and import (mock the eMAG call or use the existing live-test marker).

**Exit criterion:** the user can add a product from the UI, see it in the table, edit its price (a new price point appears), delete it, and import one from eMAG; the list refreshes without a manual reload.

### Wave 1 — data-real modules (2–3 PRs, S/M each)

1. **Review Mining:** feature → sentiment table per product/brand with positive/neutral/negative counts, score, mention count, and example sentences extracted from `review.content`; add a "mixed" label; a "recurring problems" list with exact counts and a "thin sample" badge when count < 3.
2. **Brand Health:** per-brand weekly sentiment series, positive/negative mention counts, SOV formula and source/period caveat in the API and UI, CSI.
3. **Price Intelligence:** consecutive-point change, drop detection, price-vs-rating scatter, rule-based anomaly with "no anomaly detected" and "not enough points" states.
4. **Competitor Benchmarking:** brand radar, 2+ brand selector, sample-size warning, CSI, positioning map retained.

### Wave 2 — composite scores (2 PRs, M each)

1. **Product Radar:** `POST /api/products/sync-all` (calls `sync_all_products`), a change feed, the Competitiveness Score with configurable weights and coverage, spec comparison within category only.
2. **Trend Discovery:** append-only trend history, a momentum score with per-component values and nulls, low-confidence labels.
3. **Market Opportunity Finder:** Opportunity Score with component coverage and raw inputs.
4. **Small riders:** Keyword Intelligence extensions, content-based Product Recommendation Engine, Executive Dashboard.

### Wave 3 — packaging and ML (2–3 PRs, M/L)

1. **Automated Business Reports:** on-demand report from existing services; CSV + Excel first, then PDF + PPTX; background generation; download.
2. **Customer Segmentation ML:** review-level feature matrix, K-Means + PCA, silhouette, exploratory label; rename the page to "Audience segments" unless a customer table is approved.
3. **Marketing Campaign Lab:** campaign/variant/result tables, CRUD, simulator as an assumption calculator with visible formulas.

### Wave 4 — needs new data (defer)

- True Competitor Alerts (scheduler + notifications).
- Product Lifecycle Tracker (launch dates).
- Multi-retailer price comparison (retailer column + connectors).
- Weekly/monthly scheduled reports (runner).
- Review Authenticity at scale (larger corpus, ground truth).

### What must say "not enough data"

- Any ML cluster when n < 30 or features < 3.
- Any anomaly claim when a product has < 5 price points.
- Any trend search component when there are < 2 history rows.
- Any "recurring problem" with < 3 mentions.
- Any SOV claim without the source/period caveat.
- Any campaign estimate without the "scenario, not forecast" label.
- Any lifecycle stage without `launched_at`.

---

## 6. Risks

1. **Invented numbers from small samples.** 48 reviews, 2 negative reviews, 7 negative aspect mentions, 4 price points. Every aggregate must carry its `n`; every score must carry coverage. Mitigation: return `null` and a `sample_size` field; the UI renders "not enough data".
2. **Unstable ML.** K-Means on 48 points can produce arbitrary clusters; DBSCAN likely returns one cluster plus noise. Mitigation: show silhouette, label exploratory, never present clusters as customer truth.
3. **Anomaly detection on 4 points.** Isolation Forest cannot be trained meaningfully; the seeded series has no anomalies. Mitigation: rule-based threshold + "no anomaly detected"; require ≥ 5 points before any statistical method.
4. **Campaign Simulator overreach.** Without campaign history, any "estimated results" are invented. Mitigation: assumption calculator, formulas visible, "scenario, not forecast".
5. **Trend Momentum with static seeds.** The 5 trend rows are constants; using them as history would be fabricated. Mitigation: append-only history; null search component; label seeded rows as "sample".
6. **Market Opportunity Score with thin components.** Demand from 48 reviews, dissatisfaction from 7 mentions, competition from 1–3 products. Mitigation: coverage display; no single headline score below 3/5 components.
7. **SOV misread as market share.** The denominator is stored reviews, not the market. Mitigation: explicit formula + source/period caveat in API and UI.
8. **Review Authenticity defamation.** Heuristics can label real customers. Mitigation: signals with reasons, no "fake" verdict, no public ranking.
9. **"New launch" false claims.** `launch` is text; `created_at` is the DB insert time. Mitigation: add `launched_at`; until then "launch date not tracked".
10. **Multi-retailer claims without a retailer column.** Mitigation: add `retailer` (nullable) and show "1 retailer" until more are collected.
11. **Competitiveness Score weights as hidden policy.** Mitigation: show weights, allow configuration, show raw inputs and category size.
12. **Report generation blocking the request.** PDF/PPTX with charts can take seconds. Mitigation: background task + `status: pending` + download when ready, following the existing LLM pattern (`api/analytics.py:156-165`, `api/products.py:33-45`).
13. **LLM budget.** 1000 requests/day; report generation with LLM could burn it. Mitigation: cache, derived text first, LLM optional.
14. **Specs comparison across categories.** Heterogeneous keys. Mitigation: compare within category only; show "no comparable specs" otherwise.
15. **Dependency drift.** The ML/export libraries are installed globally but not declared; a teammate's cold setup fails. Mitigation: add them to `requirements.txt` in the same PR that first imports them, and add a smoke test that imports each.
16. **Matplotlib in a server process.** Needs a non-interactive backend. Mitigation: `matplotlib.use("Agg")` before `pyplot`; generate to a temp file; clean up.
17. **Scheduler absence.** Weekly/monthly reports and push alerts cannot be honest without a runner. Mitigation: defer, or use the OS scheduler with a documented command.
18. **Sample-relative language.** "Interest", "share", "popularity" are all relative to the 48 stored reviews. Mitigation: a global "sample" badge and a methodology note in the UI.

---

## 7. QUESTIONS for the user (numbered, a recommendation each; "all rec" answers them)

1. **Care module intră primele în demo?** Avem 10 module și un singur arc de timp. Recomandare: primul val = CRUD produse + Review Mining + Brand Health + Price Intelligence + Competitor Benchmarking; restul în valurile următoare. (Dacă răspundeți „all rec", asta înseamnă ordinea din §5.)
2. **Acceptați librării noi în `requirements.txt`?** scikit-learn, reportlab, python-pptx, openpyxl și matplotlib sunt deja instalate pe acest calculator, dar nu sunt declarate; un coleg care face setup curat nu le-ar avea. Recomandare: da, le adăugăm în același PR în care le folosim pentru prima dată.
3. **Exportul de rapoarte: acum sau mai târziu?** Recomandare: CSV + Excel acum (ieftin și robust), PDF + PowerPoint imediat după, în același val sau în PR-ul următor.
4. **Cât de complet să fie CRUD-ul de produse?** Recomandare: adăugare, editare, ștergere, import eMAG, plus câmpul `launch` editabil; fără import CSV în masă acum.
5. **Ce facem când datele sunt insuficiente pentru ML?** Recomandare: afișăm modulul cu eticheta „exploratory, n=48" și calitatea clusterelor (silhouette), niciodată cifre fără avertisment; sub 30 de observații, „not enough data".
6. **Segmentarea: clienți sau recenzii?** Nu există clienți reali (48 de recenzii, 48 de autori diferiți). Recomandare: „segmente de audiență" la nivel de recenzie, fără să inventăm clienți; o tabelă de clienți doar dacă apare o sursă reală.
7. **Comparația între comercianți: o adăugăm acum?** Recomandare: adăugăm coloana `retailer` în `price_history` acum (additive), populăm doar eMAG, iar UI-ul spune „1 retailer monitorizat"; restul când există conectori.
8. **Trend Momentum: numai din recenzii sau investim în istoric Google Trends?** Recomandare: istoric append-only pentru trenduri + componenta de căutare `null` până există minim 2 puncte; nu folosim cele 5 rânduri seed ca istoric.
9. **Campaign Lab: simulator cu ipoteze sau amânăm?** Recomandare: calculator de scenarii cu formule vizibile și eticheta „scenariu, nu predicție"; fără ML predictiv și fără rezultate inventate.
10. **Rapoarte programate săptămânal/lunar: acum sau mai târziu?** Recomandare: doar la cerere acum; programarea într-un PR ulterior, pentru că nu există scheduler în aplicație.

---

## 8. CONFIRMED / UNVERIFIED / NOT DONE

### CONFIRMED (ran or read the exact line)

- Live DB counts: 10 products, 48 reviews, 40 price points, 5 brands, 5 categories, 5 trend metrics, 6 LLM cache rows (§1.3).
- Per-product table, review sources, sentiment labels, aspect counts, rating distribution, authors, weekly volume, price ranges (§2.1).
- 48 distinct authors for 48 reviews; no repeat authors (§2.1.2).
- 2 negative reviews; 7 negative aspect mentions (§2.1.2).
- 4 price points per product; 59-day range; 4.2–14 % total range; no anomaly (§2.1.3).
- 5 trend rows, seeded constants; upsert writer; no history (§2.1.4, `seeds.py:342-348`, `trends.py:47-58`).
- 1–3 products per category (§2.1.5).
- Every `file:line` cited in §2.2, §2.5 and §3 was read in this investigation.
- No campaign/report/alert/scheduler/ML/export code exists (§2.3).
- Library versions and global installation; absence from `requirements.txt`; no venv (§2.4).
- Backend CRUD routes and their line numbers; frontend has no mutation functions and no CRUD UI (§2.5).
- `ProductCreate`/`ProductUpdate`/`ProductResponse` omit `launch` (`schemas/product.py:8-43`).
- `product.rating` and `product.review_count` are derived from stored reviews, not the market (`seeds.py:441-450`, `reviews.py:154-169`).

### UNVERIFIED (read, not run)

- Whether eMAG's current HTML still matches the selectors in `connectors/emag.py:53, 61-72, 85, 127` — no live call was made.
- Whether pytrends currently returns data from this machine — no live call was made.
- Whether Reddit OAuth credentials are configured in `backend/.env` — the file was not read (secrets policy).
- Whether the OpenRouter key is currently valid — no live call was made.
- Whether the app is currently running on 8010/5173/8020 — no port check was needed for this spec.
- Whether `pandas 3.0.1` + `scikit-learn 1.9.0` + `numpy 2.4.2` are mutually compatible in every code path — imports succeeded, but no ML code was run.
- Whether `matplotlib` can render in the server process without a display — not tested; the Agg backend is the expected fix.

### NOT DONE

- No code changes, no commits, no branches, no worktrees.
- No service starts, no Docker changes, no schema changes, no writes to the database.
- No live external calls (eMAG, Reddit, Google Trends, OpenRouter, X).
- No browser screenshots, no Playwright run, no pytest run.
- No byte-level measurement of future changes; §4.5 is a change-surface estimate, not a diff.
- No performance or load measurements.

---

## 9. Left on disk

- This file only: `.orchestration/specs/005-intelligence-modules.md`.
- No scratch directories, no scripts, no database copies, no screenshots, no temporary files.
- The live database was read only; no rows were written.

---

## USER DECISIONS (2026-11-07 17:51, binding)

Utilizatorul a răspuns: **„all rec"** — acceptă toate cele 10 recomandări din acest spec.

Deciziile rezultate:

1. **Q1 — Ordinea modulelor.** Primul val: CRUD produse + Review Mining + Brand Health + Price Intelligence + Competitor Benchmarking. Restul în valurile următoare.
2. **Q2 — Librării noi.** Da, se adaugă în equirements.txt în același PR în care sunt folosite prima dată.
3. **Q3 — Export rapoarte.** CSV + Excel acum; PDF + PowerPoint imediat după.
4. **Q4 — Amploarea CRUD.** Adăugare, editare, ștergere, import eMAG, plus câmpul launch editabil. Fără import CSV în masă acum.
5. **Q5 — Date insuficiente pentru ML.** Se afișează modulul cu eticheta „exploratory, n=48" și calitatea clusterelor; sub 30 de observații, „not enough data".
6. **Q6 — Segmentare.** Segmente de audiență la nivel de recenzie, nu clienți inventați.
7. **Q7 — Coloana etailer.** Se adaugă acum în price_history (additive), populată doar cu eMAG; UI-ul spune „1 retailer monitorizat".
8. **Q8 — Trend Momentum.** Istoric append-only; componenta de căutare rămâne 
ull până există minim 2 puncte.
9. **Q9 — Campaign Lab.** Calculator de scenarii cu formule vizibile, etichetat „scenariu, nu predicție". Fără ML predictiv.
10. **Q10 — Rapoarte programate.** Doar la cerere acum; programarea într-un PR ulterior.

**Consecință:** primul PR este CRUD-ul de produse din UI plus cele două bug-uri găsite (launch needitabil, SKU duplicat → 409).

by FiredMosquito831
