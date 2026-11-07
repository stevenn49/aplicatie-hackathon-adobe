# MarketPulse AI — prezentarea platformei

Zece slide-uri, cu ce spui pe fiecare. Cifrele sunt cele reale din baza de date la 2026-11-07: 10 produse, 5 branduri, 48 de recenzii, 40 de puncte de preț, 9 aspecte, 215 motive extrase.

---

## Slide 1 — Cârligul

**Pe ecran:** o singură frază, mare.

> „Spune-mi **de ce** clienții tăi sunt nemulțumiți — nu doar **cât de** nemulțumiți."

**Ce spui:**

Echipele de marketing nu duc lipsă de date. Au recenzii pe eMAG, interes de căutare pe Google, discuții pe Reddit, prețuri în cinci magazine. Ce nu au e răspunsul la întrebarea care contează: *de ce*.

Un scor de sentiment de 62 nu îți spune ce să repari. „Bateria se descarcă repede — spus în patru recenzii" îți spune.

---

## Slide 2 — Problema, concretă

**Pe ecran:** două coloane.

| Ce ai azi | Ce îți trebuie |
| --- | --- |
| 48 de recenzii de citit manual | motivul, în 3 secunde |
| Un scor mediu de 76,1 | care aspect trage scorul în jos |
| „Prețul e mare" în 15 formulări | o singură problemă, cu 15 dovezi |
| Date în 4 locuri diferite | o singură suprafață |

**Ce spui:**

Un analist care citește 48 de recenzii, pe 10 produse, la fiecare ciclu, petrece aproximativ o oră și jumătate. Și o face din memorie: la final are o impresie, nu o dovadă. Când vine managerul de produs și întreabă „de unde știi?", răspunsul e „am citit".

Noi am construit partea care lipsește: dovada.

---

## Slide 3 — Ce face platforma

**Pe ecran:** cele opt pagini, ca o hartă.

**Ce spui:**

MarketPulse AI e o platformă de inteligență de piață pentru produse tech. Acoperă opt suprafețe:

- **Market Overview** — starea pieței: produse urmărite, recenzii analizate, sentiment mediu, preț mediu, evoluție, mențiuni, mișcări de preț
- **Product Analysis** — tabel, comparație până la patru produse, specificații, istoric de preț, argumente pro și contra
- **Brand Intelligence** — unde stă fiecare brand, pe fiecare temă
- **Sentiment Analysis** — distribuție, trend, aspecte, nor de cuvinte, explorator de recenzii
- **Consumer Insights** — cinci segmente, cu mărime, cheltuială și driveri
- **Marketing Analytics** — tendințe, unde se duce conversația, oportunități identificate de model
- **Competitor Analysis** — poziționare, diferențe de preț, matrice de features
- **AI Recommendations** — ce să faci în continuare, cu dovada atașată

Toate citesc din aceeași bază de date. Niciun număr nu e scris de mână.

---

## Slide 4 — Lucrul care ne diferențiază: Review Mining

**Pe ecran:** o recenzie reală, cu o frază evidențiată, și alături răspunsul structurat.

**Ce spui:**

Aici e miezul. Nu clasificăm recenziile în pozitive și negative — asta face oricine. Extragem **motivul**.

Pentru fiecare aspect al unui produs, platforma întoarce fraza concretă din recenzie care l-a determinat, polaritatea ei, și **ID-urile recenziilor** care o susțin.

Rezultatul pe datele noastre: **215 motive extrase din 48 de recenzii, pe 9 aspecte.** 22 de probleme recurente, 82 de lucruri apreciate.

Și aici e partea care contează: **fiecare frază e verbatim din textul recenziei.** Am verificat toate cele 215 comparându-le cu recenziile aduse prin API. Zero invenții. Dacă textul nu susține un motiv, nu se emite niciunul — o listă goală e un răspuns cinstit, o frază inventată nu e.

**Ce arăți pe ecran, dacă ai timp:**

```json
{ "aspect": "Price & value", "score": 28.9, "mentions": 19, "polarity": "negative",
  "reasons": [ { "phrase": "The price is high", "mentions": 2, "review_ids": [4, 39] } ] }
```

---

## Slide 5 — De ce AI-ul e esențial, nu un adaos

**Pe ecran:** o diagramă simplă — date → aspecte → motive → decizie.

**Ce spui:**

Suntem conștienți că „AI" a ajuns un cuvânt pe orice slide. Deci concret: dacă scoți AI-ul din MarketPulse, nu rămâi cu produsul fără o funcție — rămâi cu un tabel de numere.

Inteligența e în trei locuri, toate de neînlocuit:

**Unu — motorul de analiză a aspectelor.** Descompune fiecare recenzie în propoziții și clauze, atribuie fiecare clauză aspectelor pe care le atinge, și calculează polaritatea la nivel de clauză, nu de recenzie. O recenzie poate lăuda bateria și critica prețul în aceeași frază. Un clasificator global ar rata asta.

**Doi — asistentul, legat de datele reale.** Nu e un chatbot generic. Primește contextul paginii pe care ești, graficele montate în acel moment, filtrele active, și istoricul conversației. Când l-am întrebat cât e sentimentul pentru Samsung, a răspuns 82,9 — valoarea din MySQL. Nu dintr-un fișier de test.

**Trei — generarea cu buget adaptat modelului.** Bugetul de output nu e hardcodat: îl citim din metadata fiecărui model (`max_completion_tokens`) și cerem reasoning cu efort ridicat. Un model de raționament care primește prea puși tokeni întoarce text gol — am măsurat asta, și de aceea bugetul se derivă, nu se ghicește.

---

## Slide 6 — Integrări externe

**Pe ecran:** tabelul, cu starea reală a fiecăreia.

**Ce spui:**

| Sursă | Cum | Stare |
| --- | --- | --- |
| **eMAG** | catalog public, extragere HTML cu rate-limiting | **activ** — a adus un MacBook Air real la 6.299,99 RON |
| **Google Trends** | `pytrends`, interes de căutare pe categorie | **activ** |
| **Hacker News Algolia** | API public, fără autentificare | **activ** |
| **Reddit** | conector cu suport OAuth | implementat, inactiv fără credențiale |
| **X / Twitter** | API v2 cu bearer token | implementat, inactiv — free tier închis în feb. 2026 |
| **OpenRouter** | gateway LLM, model free | **activ** — toate cele patru suprafețe AI |

Suntem transparenți despre ultimele două: conectorii există și funcționează, dar politicile de acces din 2026 cer fie OAuth înregistrat, fie credite plătite. Nu pretindem că avem date de acolo când nu avem.

---

## Slide 7 — Arhitectura

**Pe ecran:** cele patru procese și fluxul.

```
React 18 + Vite  ──HTTP──▶  FastAPI (8010)  ──SQLAlchemy──▶  MySQL 8.4
                                    │
                                    └──▶  Asistent (8020)  ──▶  OpenRouter
```

**Ce spui:**

Backend-ul e construit ca o platformă, nu ca o aplicație monolitică. **30 de endpoint-uri REST**, documentate automat prin OpenAPI, vizibile în Swagger UI la `/docs` — link direct din sidebar.

Fiecare modul de analiză e un serviciu independent: sentiment, review mining, prognoză, recomandări, LLM. Adăugarea unei componente noi înseamnă un serviciu nou plus un endpoint, fără să atingi restul.

Asistentul rulează ca proces separat, ca să nu blocheze API-ul principal când modelul e lent.

---

## Slide 8 — Fiabilitate, cu dovezi

**Pe ecran:** rezultatele testelor, ca output de terminal.

**Ce spui:**

Am construit sub o regulă pe care o aplicăm mecanic: **niciun număr afișat nu are voie să fie inventat.**

Concret, asta a însemnat să eliminăm, pe parcurs, tot ce era placeholder: mock-uri în frontend, cifre scrise de mână în JSX, un fallback care fabrica scoruri de trend, și un asistent care răspundea dintr-un snapshot vechi în timp ce baza de date avea alte valori.

Testele:

```
89 passed, 3 skipped        backend (pytest)
35 passed                   end-to-end (Playwright, browser real)
build exit 0                frontend
```

Iar pentru modulele noi, invarianți verificați, nu doar teste de formă:

- `mentions` e întotdeauna egal cu numărul de recenzii citate — verificat pe toate cele 215 motive
- fiecare frază e verbatim într-una din recenziile citate — verificat pe toate cele 215
- un filtru fără rezultate întoarce liste goale și `reviews_analysed: 0`, niciodată un scor fabricat
- un produs inexistent întoarce 404, nu o listă goală

---

## Slide 9 — Experiența

**Pe ecran:** aplicația, cu panoul Ask AI deschis peste dashboard.

**Ce spui:**

Butonul **Ask AI** stă plutitor, în colț, pe orice pagină. Îl apeși și se deschide o fereastră peste dashboard — nu te scoate din context, nu te duce pe altă pagină. Întrebi despre ce vezi în fața ta.

Asistentul știe ce grafice sunt montate pe pagina curentă: fiecare card are propriul buton „Analyse", care îi trimite graficul respectiv ca subiect. Răspunsul vine în streaming, formatat — titluri, liste, tabele — cu un cursor care arată că încă scrie, și un buton Stop care oprește imediat.

Restul platformei urmează aceeași regulă: fiecare cifră de pe ecran are o sursă pe care poți da click.

---

## Slide 10 — Cost și valoare

**Pe ecran:** două coloane — cost lunar, valoare.

**Ce spui:**

**Costul de rulare, azi:**

| Componentă | Cost |
| --- | --- |
| Model LLM (OpenRouter, free tier) | 0 |
| eMAG, Google Trends, Hacker News | 0 |
| MySQL în Docker, local | 0 |
| Hosting pentru prototip | 0 |

Platforma rulează complet cu **zero cost de licență sau de API**. Asta nu e un accident — e o decizie de arhitectură: bugetul de output se citește din metadata modelului, deci schimbi modelul dintr-o variabilă de mediu, fără să rescrii nimic.

**Valoarea, estimată:**

Un analist care citește manual 48 de recenzii pe 10 produse, la fiecare ciclu, petrece aproximativ 1,5 ore. Săptămânal, asta înseamnă ~6 ore pe lună doar pentru citit — fără sinteză, fără comparație între branduri, fără urmărirea în timp.

Platforma face asta în câteva secunde, și în plus produce lucrul pe care omul nu îl produce: **dovada**.

La scară — 500 de produse, 10.000 de recenzii — diferența nu mai e de timp, e de fezabilitate. Un om nu poate citi 10.000 de recenzii. Platforma da.

---

## Închidere

**Ce spui:**

Am construit un prototip care rulează cap-coadă, pe date reale, fără nimic simulat. Fiecare cifră din interfață vine din baza de date. Fiecare motiv din Review Mining e o frază pe care o poți găsi în recenzia citată.

Următorul pas nu e să adăugăm funcții — e să adăugăm **surse**: Reddit cu OAuth, X cu credite, mai mulți retaileri. Arhitectura e făcută pentru asta: un conector nou, un serviciu nou, un endpoint nou.

---

## Anexă — ce să nu spui

Ca să nu te prindă juriul:

- **Nu spune „API-ul eMAG".** eMAG nu are API public. E extragere din catalogul public prin HTML. Spune „catalog public" sau „scraping cu rate-limiting".
- **Nu spune „API-ul Google Trends".** E `pytrends`, o bibliotecă neoficială care citește interfața web. Spune „Google Trends prin pytrends".
- **Nu spune că ai date din Reddit sau X.** Conectorii există, dar sunt inactivi fără credențiale. Spune „implementați, inactivi în prototip".
- **Nu spune „PostgreSQL cu Supabase" la prezent.** Prototipul rulează pe MySQL. Spune „MySQL pentru prototip, PostgreSQL pentru producție" — e o decizie, nu o confuzie.
- **Nu inventa cifre de economie.** Spune „estimare" și arată calculul, cum e mai sus.

by FiredMosquito831
