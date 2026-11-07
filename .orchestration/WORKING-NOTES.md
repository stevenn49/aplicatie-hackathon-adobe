# Working Notes — the operating manual for MarketPulse AI

The orchestrator's manual: how the user works, what they verify and reject, repo and release mechanics, CI and code rules, product principles, domain facts, how agents are run, the machine, every release, every learning, and what is still open. **Current truth only.**

- **Where it lives:** `D:\Projects2\adobe hackathon\aplicatie-hackathon-adobe\.orchestration\` (inside the repo; gitignored by default — see PART X).
- **Before editing:** copy it to `WORKING-NOTES.bak-<yyyy-mm-dd-hhmm>.md` beside it. Never modify or delete a `.bak*`.
- **Format:** UTF-8, CRLF. Append a line with a script that reads `newline=""`, asserts its anchor exactly once, and writes the same newline. Never `sed -i`/`awk` on it.
- **Who edits:** only the orchestrator. Agents never edit it — they report lessons in their final message and the orchestrator ports them.
- **No secrets** here, ever; machine paths as `~` / `%USERPROFILE%` where possible.
- **History and the dated diary** live in `WORKING-NOTES-ARCHIVE.md` (same folder): every superseded block, every dated diary line, long version-table cells — verbatim, with an index; cite old section numbers as `(§N)` and never renumber them, because specs cite them. The dated running log is `HANDOFF-<first date>.md`; the current entry point is the newest `HANDOFF-<date>.md`; the PR queue is `QUEUE.md`; specs and their USER DECISIONS blocks are in `specs/`.

## Map of this file

| Part | What lives here |
| --- | --- |
| I — How the user wants to work | ownership, discuss-first, delegation, how they verify, what they reject, communication, standing decisions |
| II — Repo mechanics | checkout + worktrees, versioning, the release process and its traps, PR/commit shape, the verify recipe, hard rules for every brief |
| III — CI, testing, code rules | the gate, flakes, test isolation, banned patterns, boundaries, contract tests, new-setting checklist |
| IV — Product principles | the rules every change is judged against |
| V — Domain facts and gotchas | what this system's parts actually do (filled over time) |
| VI — Subagent orchestration | the loop, briefs, resume, failure modes |
| VII — Environment | this machine, disks, tools |
| VIII — Release history | one row per version |
| IX — Learnings | one deduplicated list, grouped by theme, each with its origin |
| X — Still open | deferred work, queue pointers, the user's own to-dos |

**Fastest cold start:** the newest HANDOFF → PART I → II.5 → II.6 → IV → the last ten rows of PART VIII → X.

---

# PART I — HOW THE USER WANTS TO WORK

## I.1 Ownership and what "done" means
- Their repo, their merge: `stevenn49/aplicatie-hackathon-adobe` (remote `origin`); the user is a collaborator. No upstream that must never receive pushes. Pushing still waits for the user's explicit go each time.
- **Merged is not shipped.** Shipped = committed + pushed + merged to `main` + the app runs end to end on the user's machine with the real database, backend and frontend.
- Finish end to end. "Fixed" means the user can see it working: state the exit criterion in their terms up front, test to it, lead with the negative when it is negative.
- Good behaviour by default: never a "run this once" user step; the product does it.
- The live system is theirs: there is no deployed live service at the time of writing (2026-11-07). Local only.

## I.2 Discuss before building
- Read-only investigation → a spec in `specs/` with NUMBERED plain-language questions, each with a recommendation → the user answers in one line → a binding `USER DECISIONS (<time>)` block appended to the spec → ONE implementer. Never dispatch before they agree.
- A small ask must not fan out; scope beyond the literal request is a question BEFORE dispatch.
- Safest, 100 % working, break nothing: change only what is broken, where it is broken; equality contracts prove behaviour-preserving work; what cannot meet the bar is left out and named.
- Investigations finish before fixes start on the same question.
- Questions the user can answer: plain language, only about things they can see or decide; never relay an agent's question unchecked.
- Queue discipline: finish the QUEUED PRs first in their order; new ideas wait; after the last queued PR, report and let the user choose.
- Granular PRs: one concern per PR and per release; scope additions go to the NEXT PR unless one line.
- External publication waits for an explicit go.

## I.3 Delegation, model choice, context
- Delegate the investigation AND the spec-writing; take conclusions only. Protect the orchestrator's context.
- Every agent inherits the session's model. At most 2 agents at once; one implementer at a time; read-only investigators may run beside it.
- One written spec per implementer: enumerated contract, every `file:line` grepped, tests named, docs, verification.
- Announce every dispatch in the same message. No extra process artefacts beyond the ones named above.
- No diagnostics of their machine unless asked. Agents keep `PROGRESS.md` + `HANDOFF.md` so a pause or kill costs nothing. No infinite or background polling anywhere.

## I.4 How they verify
- They test independently and come back with counter-evidence. Assume every claim will be checked on their machine.
- Their bug reports are precise and usually right: reproduce first, argue never.
- "Did you fix it" is often honestly "no, and here is what I actually verified".
- When they are frustrated: lead with evidence, not reassurance.

## I.5 What they reject
- Invented limits; claiming it works without running it; low-effort deliverables and filler docs; docs in the wrong place; a UI never driven in a browser; per-name fixes; speculative features; changes to retry/fallback/rotation/safety behaviour; a long page as a fix; being told to change their settings.
- Placeholders, mock data and hardcoded numbers presented as real product behaviour.

## I.6 Communication style
- Lead with the answer, then the evidence; show real command output rather than describing it.
- Say plainly when wrong, correct it, move on.
- Separate **CONFIRMED** (ran it; output shown), **UNVERIFIED** (read it), **NOT DONE** (skipped, and why).
- The machine is Europe/Bucharest (UTC+2/+3 DST); every DB timestamp is UTC — convert before saying "recent".
- The user works in Romanian. Prose answers in Romanian; code, identifiers, commit messages and file contents in English.

## I.7 The user's standing decisions (do not re-ask)
- 2026-11-07: The prototype must be 100 % functional and tested end to end — backend, frontend, and in a real browser with automation (Camoufox).
- 2026-11-07: Local database is **MySQL**, not PostgreSQL and not Supabase.
- 2026-11-07: The LLM is reached through **OpenRouter** with a free model the user chooses (1000 requests/day budget). The user supplies the API key when needed.
- 2026-11-07: All features must be tested, including the ones that need external APIs.
- 2026-11-07: Work in Romanian for prose.

---

# PART II — REPO MECHANICS

## II.1 Checkout, worktrees, branches
- Checkout: `D:\Projects2\adobe hackathon\aplicatie-hackathon-adobe`. One fresh worktree per unit of work from `origin/main`: `git -C <checkout> fetch origin` then `git -C <checkout> worktree add -b <branch> <WORKTREE ROOT>/<id> origin/main`. Scratch data in `D:\Projects2\adobe hackathon\.scratch\<id>`; read-only investigators in `<WORKTREE ROOT>/inv-<topic>`.
- Never delete anything under `<WORKTREE ROOT>`/`<SCRATCH ROOT>` — list leftovers; the user deletes on request.
- Never `git stash`, `git checkout <file>`, `git reset` in a worktree. Inspect with `git diff`; compare against a base in a SECOND detached worktree.
- Branch names mirror the commit type (`fix/`, `feat/`, `docs/`, `perf/`, `chore/`, `test/`); squash-merge, delete the branch.
- Re-anchor before analysing: `git log --oneline -1 origin/main` and `git log --oneline HEAD..origin/main | wc -l`.
- Line endings: the repo is CRLF on disk on Windows; `.gitattributes` is absent. Scripted edits must detect the file's newline and write the same one.
- One implementer at a time (two in flight always conflict on `package.json` / `requirements.txt`).

## II.2 Versioning
- No release process exists (no tags, no CI, no `.github/`). The version is `1.0.0` in `package.json` and `"1.0.0"` in `backend/main.py`'s FastAPI constructor.
- Rule adopted 2026-11-07: bump PATCH for fixes, MINOR for new endpoints/pages, MAJOR never during the prototype. Bump both places in the same commit. No tags until the user asks.

## II.3 Release process
1. Bump in the same commit as the source change.
2. Commit (II.4) → push (only with the user's go) → open a PR against `main`.
3. There is no CI. The gate is III.1, run locally, and reported with real output.
4. Squash-merge with `--delete-branch` after the user approves.
5. No artefact, no release, no tag. "Shipped" = merged to `main` + the local app runs end to end.
- Release notes are the only changelog: headline → what was wrong, with measured evidence → what to expect → action required, with the exact command → known and deliberate.
- Traps that bit: `node_modules/` (89.8 MB) is committed to the repo; never re-add it, and never `git add -A` at the root.

## II.4 PR and commit shape
- Commit message: conventional prefix, then prose: what was broken → the mechanism (cause, not symptom) → what the fix does and any non-obvious choice → verification with real output → what was deliberately not done. Attribution line: `by FiredMosquito831`.
- PR body: the same structure with headings, real output in fenced blocks, a **Residual risks** section always ("none" if none).
- Never claim verification beyond what ran.

## II.5 The verify recipe (after every "shipped" report, before relaying)
```
git -C <checkout> fetch origin --tags ; git -C <checkout> log -1 --format='%h %s' origin/main
gh pr list --repo stevenn49/aplicatie-hackathon-adobe --state open
git -C <checkout> diff origin/main~1 origin/main --stat
docker ps --filter name=marketpulse-mysql            # the DB container is up and healthy
mysqladmin -h 127.0.0.1 -P 3307 -u marketpulse -p*** ping
curl -s http://127.0.0.1:8000/health                 # {"status":"online","database":"healthy"}
curl -s http://127.0.0.1:8000/api/analytics/overview # a call that does REAL work, not a health endpoint
curl -s http://127.0.0.1:5173/ -o NUL -w "%{http_code}"  # frontend serving
```
Also: LOOK at at least one screenshot the agent names; scan images for key prefixes; read the agent's deviations, residual risks and not-done list; then append the dated "SHIPPED AND VERIFIED BY ME" line (archive diary) + a PART VIII row, update the queue, tell the user (what shipped, what you verified, deviations, not done) and announce the next dispatch.

## II.6 Hard rules for every implementer brief
1. **Where:** a worktree per II.1; never the primary checkout; never stash/checkout-a-file/reset; never delete scratch; list every dir left behind.
2. **Never touch the user's world:** no deployed service exists; never touch the user's Docker volumes beyond `marketpulse-mysql`; never touch `%USERPROFILE%\.claude`; never modify the user PATH; scratch runs redirect `HOME`/`USERPROFILE` where the tool honours it and verify the child's environment before any start that could take over something real.
3. **Stopping processes:** only PIDs you started, by exact PID, children by parent id; never by image name or substring.
4. **Scratch services:** own ports from 8100-8199 (backend) and 5180-5199 (frontend) for proofs; the dev ports 8000/5173 belong to the user's running app. Check `netstat -ano | findstr :<port>` first. Fake credentials of the same prefix shape. A network guard that blocks non-loopback DNS is required only for proofs that must not reach the internet (a dead proxy is not enough — block DNS too).
5. **Secrets:** never read `backend/.env` or `.env.local` beyond the keys a task needs; never print process command lines; mask by value shape (`sk-or-v1-…`); screenshots of your own window only.
6. **Desktop/installer launches in a proof:** not applicable.
7. **Test isolation:** run with a scratch database (`marketpulse_test`), a scratch port, and the user's running app's state counted before and after.
8. **Tooling:** `python -m pytest` only from `backend/`; never bare `python` with `-c` one-liners or heredocs; scripts as files via the Write tool, run by path; never `sed -i` on tracked files; CRLF preserved.
9. **Frozen safety boundary** (the orchestrator diffs it after every ship; must be EMPTY unless the file is the PR's stated purpose): none established yet. Goldens that must pass unmodified: none yet. The security contract test: none yet — add one when secrets handling lands.
10. **Versioning and gate:** II.2 and III.1.
11. **Every new setting:** the III.6 checklist.
12. **Ship:** II.3 in full.
13. **Live external calls** only with the user's consent and a stated budget, counted in calls the retry ladder may multiply; a rate-limit answer is inconclusive. eMAG scraping, Reddit JSON, Hacker News Algolia and Google Trends are all live external calls.
14. **Reporting:** the final message IS the deliverable ("partial is acceptable, silence is not"); keep `PROGRESS.md` + `HANDOFF.md` in the worktree from the first edit and commit WIP early; bounded loops only; do not edit WORKING-NOTES — report lessons; name every screenshot and LOOK at it; list every leftover dir.
15. **Extend, never narrow:** list every module the change touches (grepped, `file:line`) and read each before changing anything; when the change meets an existing mechanism, add to it and keep every existing output byte-identical (equality proof); if the scope seems to require removing or bypassing existing behaviour, STOP and report.

**Brief skeleton that works:** see `templates/BRIEF-IMPLEMENTER.template.md` in the skill.

---

# PART III — CI, TESTING, CODE RULES

## III.1 The gate
- Backend: `cd backend && python -m pytest tests -q` (repo-wide; no file-scoped runs).
- Frontend build: `npm run build` at the repo root (must exit 0).
- End-to-end: `npx playwright test` against a scratch backend port + scratch MySQL database.
- Browser automation for visual proof: Camoufox MCP.
- Local is the gate; there is no CI.
- Baseline at 2026-11-07: the backend "tests" are print-based scripts with no assertions on most paths and live network calls; treat a green run as meaningless until they are converted.
- Risk tiers (decide from the paths in the diff; when unsure, tier up): T0 docs/tests/CI only → the gate; T1 UI only → build + a screenshot looked at; T2 source outside the frozen boundary → gate + targeted tests + behaviour on a scratch instance + mutation checks for new guards; T3 anything that rewrites stored data → full-size copy, round trip, equality, kill test, old-version reads; T4 installers/updaters/frozen files/OS branches → the full local suite + install proofs.
- Proportionate testing: tests follow the SYSTEMS the diff changes; a one-line flip gets no new tests; new tests only for new or changed behaviour.
- Never two full gates at once on the machine.

## III.2 Known flakes
- `backend/tests/test_connectors.py` hits live Reddit/HN/Google Trends — it can fail or hang on rate limits. Classification: test defect (not hermetic). Fix when touched.

## III.3 Test isolation
- Every test that touches the database uses `marketpulse_test`, created and dropped by the fixture, never the dev database `marketpulse`.
- Every network-reaching test is marked and skipped by default; live calls run only in an explicit suite with a stated budget.
- The FastAPI app's `lifespan` seeds the database; tests must override `DATABASE_URL` before importing `main`.

## III.4 Code rules that fail CI
- No `print()` as the only assertion in a test.
- No bare `except:`.
- No silent fallback that hides a configuration error (the SQLite fallback in `database/connection.py` is the current offender).
- No hardcoded product ids in seeds.

## III.5 Architecture and import boundaries
- `backend/api/*` may import `schemas`, `services`, `data_collection`, `database`; never the reverse.
- `backend/connectors/*` must not import `database` or `api`.
- `src/services/api.js` is the ONLY place the frontend talks HTTP; pages never call `fetch` directly.
- `src/mocks/*` must not be imported by any page once the real integration lands.

## III.6 Every new setting / environment variable
- Constant default → settings field → surface with real help text → bounds → example config line → docs → the contracts that pin all of that green. Everything new is opt-in and byte-stable when unset.

## III.7 Contract tests you will meet
- `test_contracts.py`: every endpoint declared in `src/services/api.js` exists on the backend and returns the shape the page consumes. This is the test that prevents the current class of bug (frontend contract vs backend contract drift).
- A leak contract: no secret in any response, log or row.

## III.8 Stored-data schema rules
- Additive columns only; versioned index names; NULL = not measured vs 0 = measured zero; backfills on the writer thread; test on a realistic copy.
- Alembic is in `requirements.txt` but has no `alembic.ini` and no `migrations/`. Either wire it properly or remove it — do not leave a half-installed migration tool.

---

# PART IV — PRODUCT PRINCIPLES

1. **No invented limits.** Never a hard-coded ceiling, budget or "sensible default" for something the other side reports; derive from what it reports.
2. **Clamp to capability, never under-use it.** Requested ≤ max → send requested; > max → send the max (never refuse, never shrink further); unknown → fall back and say so.
3. **Scope boundaries are explicit** (what installs what; what the product does vs what the user does).
4. **Guardrails must not become outages.** Soft guardrails degrade rather than refuse; single points bypass health gates.
5. **Secrets never leave the machine in identifiable form.** Masked labels only; never in a DB, log line or response; bodies redacted at write time; transport security is never weakened (contract test).
6. **General over per-name; never a name branch.** Scope is declared data (profiles, tables, learned facts).
7. **Everything new is opt-in, and stable outputs must not change.** With no new preference set, outputs are byte-identical (equality contract required).
8. **Never alter retry, fallback, rotation or safety behaviour** except as a PR's stated, user-approved purpose, with outcomes proven byte-identical. Re-verify every carried-over proposal's premise in code first.
9. **No hand-entered facts where a source exists** (prices, limits, capabilities): reported → declared → derived → NULL "not known"; never a fabricated zero.
10. **No speculative features.** Build what was asked.
11. **Every setting is visible** where it belongs, with real help text, nothing hidden by default.
12. **The user's values stay the user's.** Fixes work with their settings; never change shipped defaults or their values to "fix" a bucket.
13. **Data is never lost by a feature.** Nothing migrates or compacts automatically beyond what the user decided; destructive routes need a confirm token.
14. **Good behaviour by default, one update path.**
15. **Documentation is a deliverable and belongs where the user is.**
16. **Unknown is not unsupported.** Distinguish them at every layer.
17. **Honest product wording.** "Installed and verified" enumerates what was checked; "restarted" means it answers; a success with no answer is labelled as such.
18. **Never reduce a wide, deep system to fit one scope.** A change that touches an exhaustive mechanism improves, expands and adds — a new rung, field, case — and never narrows, replaces or bypasses it; every brief names the affected modules; every PR proves the old outputs are produced identically.
19. **No placeholder presented as product.** A number in the UI is either computed from stored data or visibly labelled as a sample.

---

# PART V — DOMAIN FACTS AND GOTCHAS

## V.1 Frontend (as of 2026-11-07, `main` = `f8b0b2c`)
- `src/services/api.js` is the only HTTP layer. `const API_URL = import.meta.env.VITE_API_URL || ""` and `if (!API_URL) return delay(fallback)` — **with no `VITE_API_URL` the whole app silently serves fixtures from `src/mocks/marketData.js`.** The root `.env.example` sets `VITE_API_URL=http://localhost:8000`, which, if copied, breaks every page because the paths do not match the backend.
- Frontend paths requested: `/analytics/overview`, `/products`, `/products/compare?ids=`, `/products/{id}`, `/analytics/brands`, `/analytics/sentiment`, `/analytics/consumer-segments`, `/marketing/trends`, `/analytics/competitors`, `/analytics/recommendations`.
- Pages also import `BRANDS`, `brandStats`, `priceHistory`, `products`, `segments` directly from `src/mocks/marketData.js` for colours, selectors and chart series — these imports survive even when `VITE_API_URL` is set.
- Hardcoded product-facing numbers baked into JSX (not from any API): `MarketOverview` "MONDAY, FEBRUARY 24, 2025" + trending NVIDIA +34.2%; `SentimentAnalysis` distribution 71/20/9 + "84.2k reviews"; `ConsumerInsights` `drivers` array + growth percentages; `MarketingAnalytics` KPI row + `opportunities` + "Where the conversation lives" bars + "Trends refreshed 4h ago"; `CompetitorAnalysis` `features`/`matrix`/`activity`; `AIRecommendations` executive summary + "84.4% avg. confidence" + "82/100 market readiness"; `BrandIntelligence` "+3.2 pts this month"; `Layout` "Northstar Labs"/"Stefan C."/badge "5"/"All sources connected"; footer "Data refreshed 4 min ago".
- Product ids in the UI are strings (`"p1"`, `"p2"`); backend ids are integers.

## V.2 Backend (as of 2026-11-07)
- Routers: `/api/products` (`api/products.py`) and `/api/analytics` (`api/analytics.py`). There is **no** `/api/marketing` router.
- Endpoints that exist: `GET /api/products/`, `GET /api/products/{id}`, `GET /api/products/{id}/detail`, `POST /api/products/`, `POST /api/products/import-from-emag`, `PUT /api/products/{id}`, `DELETE /api/products/{id}`, `GET /api/products/{id}/prices`, `GET /api/products/{id}/reviews`, `POST /api/products/{id}/collect-reviews`, `POST /api/products/{id}/sync-price`, `GET /api/analytics/overview`, `GET /api/analytics/sentiment?product_id=`, `GET /api/analytics/prices?product_id=`, `GET /api/analytics/trends`, `GET /api/analytics/recommendations`, `POST /api/analytics/refresh-trends`.
- Endpoints the frontend needs that do **not** exist: `/api/analytics/brands`, `/api/analytics/consumer-segments`, `/api/analytics/competitors`, `/api/marketing/trends`, `/api/products/compare`.
- `database/connection.py` silently falls back to SQLite when the configured URL fails — a misconfigured MySQL looks like a working app on an empty SQLite file.
- `database/seeds.py` hardcodes `product_id` 1..5 for reviews.
- `services/forecasting.py:36` uses `prices[-1]` as "oldest" while the API passes history ordered ascending — the change percentage is computed from the newest point.
- `data_collection/prices.py:70` returns `old_price` after `product.price` was reassigned — old and new are equal.
- `connectors/emag.py:167` type hint `-> (Optional[float], str)` is a tuple expression, not a type.
- `connectors/google_trends.py` falls back to `_estimate_trend`, which fabricates scores (88.0 / 72.0) — a placeholder presented as data.
- `requirements.txt` lists `psycopg2-binary` (PostgreSQL) and `alembic`; there is no MySQL driver and no `alembic.ini`.
- No LLM integration exists anywhere. "AI recommendations" are rule-based thresholds in `services/recommendations.py`.

## V.3 Data sources
- eMAG: HTML scraping of public search/product pages (`connectors/emag.py`), rate-limited 1.5 s. Fragile by nature; selectors are `.card-item, .card-v2, [data-card-type='product']`.
- Reddit: public `.json` endpoints, no auth.
- X/Twitter: v2 API, requires `TWITTER_BEARER_TOKEN`; returns `[]` without it.
- Google Trends: `pytrends`, falls back to fabricated estimates.
- Hacker News Algolia: open, no auth (`connectors/alternative_reviews.py`).

---

# PART VI — SUBAGENT ORCHESTRATION

## VI.1 The loop that holds up
1. Re-anchor (default branch head, latest release, open PRs, worktrees, the live system's version, `ListAgents`).
2. Read-only investigator → a spec in `specs/` with numbered questions + a recommendation each.
3. The user answers; append the answers verbatim as a binding `USER DECISIONS (<time>)` block.
4. ONE implementer from the spec + the decisions + the II.6 hard rules, in a fresh worktree; it ships PR → gate → merge.
5. Verify every claim yourself (II.5), LOOK at the screenshots, relay: what shipped, what you verified, deviations, not done. Port the lessons here. Announce the next dispatch.

Investigators disagree; the implementer measures both sides. Scope additions can be folded into a RUNNING agent by message without loss; larger ones go to the next PR.

## VI.2 What goes wrong with agents, and the counter-measure
- Silence → the brief says the final message IS the deliverable.
- Kills (limits, crashes) → `PROGRESS.md` + `HANDOFF.md` from the first edit, WIP committed; resume the SAME agent by message with the on-disk state; across sessions, a fresh agent from the HANDOFF.
- Waiting forever / polling forever → bounded loops with timeouts only.
- Stray agents → `ListAgents` before every dispatch.
- Wrong claims → budget half to be wrong; check every `file:line`; "unchanged" claims about machine state need the before/after diff shown.
- Writing to the wrong notes file → briefs forbid editing the manual.
- Specs written from reading are wrong about third-party tools → install and read the real thing first.
- A cut-off launch brief → check `ListAgents`, re-send the full brief by message.

## VI.3 What a read-only investigator brief says
READ-ONLY: no git writes, no edits outside its scratchpad and the spec, never touch the live system (GET-only at most), never print secrets, open data copies read-only, a stated live-call budget (or none), where to write the spec, the numbered questions to answer, CONFIRMED vs UNVERIFIED separated, "a process scan is not proof a service is unused".

---

# PART VII — ENVIRONMENT

- Machine: Windows 11 Pro 10.0.26100, PowerShell 7 primary, Git Bash also available.
- Checkout: `D:\Projects2\adobe hackathon\aplicatie-hackathon-adobe`.
- Timezone: Europe/Bucharest. DB timestamps UTC.
- Node v24.6.0, npm bundled. Python 3.13.7.
- Docker 29.8.0, daemon running. **MySQL is NOT installed natively** — no service, no `mysql.exe`, nothing on 3306. The local database runs in Docker (container `marketpulse-mysql`, host port 3307).
- **Port 8000 is occupied by an unrelated local Python service** (a document-conversion API answering `0.0.0.0:8000`). The backend therefore runs on **8010**. Never kill that process; it is not ours.
- Python packages present globally: fastapi 0.133.1, uvicorn 0.41.0, SQLAlchemy 2.0.47, pydantic 2.12.5, pydantic-settings 2.13.1, httpx 0.28.1, beautifulsoup4 4.14.3, pytest 9.0.2, playwright 1.58.0, PyMySQL 1.4.6, vaderSentiment 3.3.2, pytrends 4.9.2, python-dotenv 1.0.1.
- Ports: 8010 backend, 5173 Vite dev. Scratch proofs: 8100-8199 and 5180-5199.
- `node_modules/` is committed to the repo (89.8 MB) — do not re-add, do not delete from git without the user's go.
- The MySQL `marketpulse` user has ALL on `marketpulse.*` and `marketpulse_test.*`; the test suite creates and drops `marketpulse_test` itself.

---

# PART VIII — RELEASE HISTORY

| Version | Date | PR | What |
| --- | --- | --- | --- |
| (seeded) | 2026-11-07 | — | Repo cloned at `f8b0b2c` on `main`. Seeded from git log: `5f5aad2` clean start → `3de31f3` final frontend commit → `081216c` FastAPI backend → `f8b0b2c` merge of `feature/add-backend`. No releases, no tags, no CI. |
| 1.1.0–1.7.0 | 2026-11-07 | local | The integration arc: MySQL in Docker on 3307 with no silent fallback; the five missing endpoints; the five reshaped ones; mocks and hardcoded numbers removed; four data-integrity bugs fixed; pytest + Playwright suites. Gate: 56 pytest passed / 3 skipped, 32 Playwright passed, `npm run build` exit 0. Deviations: backend on 8010 because 8000 is taken on this machine. Not done: OpenRouter key and model id (LLM surfaces report `derived`). |
| 1.8.0 | 2026-11-07 | #4 | One interactive launcher in the repo root (`run.ps1` / `run.sh`), a guided setup that detects Docker vs native MySQL and asks for each API key, a settings manager, and `POST /api/admin/reload` so a key applies without a restart. |
| 1.9.0 | 2026-11-07 | #4 (merge `a988877`) | OpenRouter as an assistant provider and the default; output budget read from each model's metadata with `reasoning.effort=high`; JSON extraction takes the outermost structure; the three LLM surfaces read cache-only and generate in a background task; Reddit gains OAuth. Gate: **70 pytest passed / 3 skipped**, **32 Playwright passed**, build exit 0. Live OpenRouter calls verified on all four surfaces. |

---

# PART IX — LEARNINGS (consolidated, deduplicated)

One bullet per lesson, with the evidence that makes it memorable and its origin. Rules that follow from these lessons live in PARTS I–VII; this is the "why".

## IX.1 Verification and evidence
- Re-anchor before analysing. The evidence ladder: real data through the whole path, read back from storage > the real artefact run unattended > a unit test on the changed function > reading the code.
- Verify at the layer the bug lives. A command that fails is not a command that found nothing. "No matches" needs a second command.
- Reproduce the symptom first; observability first, then debugging. The instinct to blame the newest release is usually wrong — get the daily series.
- A test that cannot fail is not a test; prove every guard against the broken case (revert and watch it fail).
- Grep every golden/baseline for the bytes a fix changes before planning it.
- 2026-11-07: A frontend that works is not evidence the backend works. `src/services/api.js` returns fixtures when `VITE_API_URL` is unset, so every page renders perfectly with zero backend running. Check `import.meta.env` before believing a screenshot.

## IX.2 Agents and briefs
- (none yet)

## IX.3 Shell and tooling traps on this machine
- 2026-11-07: `Get-ChildItem -Force` on an empty directory prints nothing before the next section — do not read an empty listing as a failed command.
- 2026-11-07: The repo has no `.gitattributes`; files are CRLF on disk. Any scripted edit must preserve CRLF.

## IX.4 Domain
- 2026-11-07: The frontend and backend were built independently and never connected. Ten endpoints are requested; five exist; zero match in shape. The contract test in III.7 exists because of this.
- 2026-11-07: MySQL 8.4 removed `--default-authentication-plugin`. Passing it makes mysqld abort with `unknown variable`, and the entrypoint then leaves a half-initialised data directory that reports `Table 'mysql.plugin' doesn't exist` on every retry. Drop the flag and recreate the volume.
- 2026-11-07: A port can be owned by two processes at once on Windows when one binds `0.0.0.0` and the other `127.0.0.1`. `Get-NetTCPConnection -LocalPort 8000` showed both; the `0.0.0.0` listener answered the request. Always check the wildcard bind, not just the loopback one.
- 2026-11-07: A passing UI is not a passing product. The dashboard rendered perfectly for weeks with no backend at all. The Playwright suite now asserts against the API response, not against the rendered text alone.
- 2026-11-07: A free model can be listed and still be unusable. `stealth/crouton-alpha` is the largest free model on OpenRouter and answers `403 This model is not available in your region` from this network. Probe the catalogue from the machine that will run the app before choosing a default.
- 2026-11-07: A reasoning model spends the output budget thinking. `dots-3-note-preview` returned an empty `content` with `finish_reason=length` at 900, 2000 and 4000 max_tokens, and only produced JSON at 8000 (5,284 of them reasoning). Read `top_provider.max_completion_tokens` from `/api/v1/models` and size the request from it; never assume a small budget is enough.
- 2026-11-07: A 50-second endpoint looks like a broken app. The product drawer blocked on the LLM call and the Playwright suite failed on the first run, then passed on the second because the cache was warm. Read the cache, answer immediately, generate in a `BackgroundTask`, and label the state `pending`.
- 2026-11-07: Reddit's public `.json` endpoints returned `403` on 2026-11-07. Reddit requires OAuth since 2026; the connector now authenticates and reports `last_status` instead of returning an unexplained empty list.
- 2026-11-07: The X/Twitter free tier closed to new developers on 2026-02-06. Access is pay-per-use (~$0.005 per post read) and a bearer token alone returns 402 without credits. Treat X as a paid source, not a free one.
- 2026-11-07: `Start-Process` children hold inherited console handles, so a script that starts a server and then `exit`s leaves the host waiting. `[Environment]::Exit(0)` in the detach path is what actually returns control.
- 2026-11-07: A `$script:` variable set by the caller is not reliably visible inside functions defined in a dot-sourced file. Use `$global:` for the non-interactive flag, and guard prompts with `[Console]::IsInputRedirected` so a scripted run never blocks on `Read-Host`.

---

# PART X — STILL OPEN

- **Amendment 2026-11-07:** `.orchestration/` **is committed** — the user asked for the tracking files to live in the repo because the team works cumulatively. Only `*.bak-*` copies stay untracked.
- **Priority now:** the integration arc is complete and green locally. Next: commit + push, then the OpenRouter key so the LLM surfaces can be proven against the real model.
- **Awaiting the user's decision:** the OpenRouter API key and the exact free model id; whether to remove `node_modules/` from git history.
- **Known unqueued findings** (re-verify before citing): `node_modules/` is still committed (89.8 MB); there is no CI; `datetime.utcnow()` is deprecated in Python 3.13 and emits warnings across the models and services.
- **The user's own to-dos:** supply the OpenRouter key and model id.
