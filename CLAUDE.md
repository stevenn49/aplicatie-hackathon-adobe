<!-- working-notes:begin (managed by the working-notes skill; edit inside only through /working-notes) -->
## How we work in this repo (orchestration)

**Entry points (read in this order at the start of every session):** the newest `.orchestration/HANDOFF-<date>.md` → `.orchestration/QUEUE.md` → `.orchestration/WORKING-NOTES.md` (PART I, II.3, II.5, II.6, IV, X, the dated lesson lines at the end). Specs and their binding `USER DECISIONS` blocks live in `.orchestration/specs/`. Verify the live state before relaying anything; report in five lines or fewer; do not dispatch before the user's go.

**Binding rules (the full text is WORKING-NOTES; these are the ones that are never relaxed):**
1. Discuss before building: read-only investigation → spec with numbered questions + a recommendation each → the user's one-line answers → `USER DECISIONS (<time>)` appended to the spec → ONE implementer. Never dispatch before the user agrees.
2. Safest, 100 % working, break nothing: change only what is broken, where it is broken; behaviour-preserving work is proven by equality contracts; extend, never narrow an existing mechanism; stop and report if the scope seems to require removing behaviour.
3. One production PR at a time; one concern per PR and release; at most two agents; agents inherit the session's model; announce every dispatch; every agent keeps `PROGRESS.md` + `HANDOFF.md` in its worktree from the first edit.
4. The orchestrator verifies every "shipped" claim itself (WORKING-NOTES II.5): merge = default branch, the frozen diff empty, the security grep 0, the gate read by name, a screenshot looked at, the app doing real work against MySQL. CONFIRMED / UNVERIFIED / NOT DONE, always separated.
5. Tracking at every PR boundary: `QUEUE.md` (RUNNING / QUEUED / FINISHED / HELD), a release-history row and dated lesson lines in WORKING-NOTES (backup before every edit; line endings preserved), one line per event in the dated log; a `HANDOFF-<date>.md` before every pause or compaction.
6. Never touch the user's world: no deployed service exists; never touch the user's Docker volumes beyond `marketpulse-mysql`; never touch `%USERPROFILE%\.claude`; never modify the user PATH; never read `backend/.env` or `.env.local` beyond the keys a task needs; scratch runs use scratch databases, own ports (8100-8199 / 5180-5199), fake credentials of the same prefix shape; stop only PIDs you started, by exact PID; never delete under `D:\Projects2\adobe hackathon` (list leftovers).
7. Frozen boundary: none established yet. Goldens: none yet. Never alter retry / fallback / rotation / safety behaviour otherwise.
8. Tooling: `python -m pytest` from `backend/` only; never bare `python` with `-c` one-liners or heredocs into an interpreter; scripts as files run by path; never `sed -i` on tracked files; repo-wide checks; never two full test gates at once; CRLF preserved.
9. Product principles: no invented limits; clamp to capability; unknown ≠ unsupported; everything new opt-in and byte-stable when unset; honest wording; data never lost; general over per-name; no speculative features; docs where the user is; **no placeholder presented as product**.
10. Live external calls only with the user's consent and a stated budget; a rate-limit answer is inconclusive. eMAG scraping, Reddit JSON, Hacker News Algolia, Google Trends and OpenRouter are all live external calls.

**Attribution:** commits and PR bodies end with `by FiredMosquito831`.
<!-- working-notes:end -->
