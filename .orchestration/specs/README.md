# specs/

One file per investigation or unit of work, named `NNN-slug.md`. Structure follows the working-notes `SPEC.template.md`:

- `# INVESTIGATION — <TOPIC> (<date>, read-only)`
- `## 0. Answer in five lines`
- `## 1. The problem as reported and the reproduction`
- `## 2. Measured findings (CONFIRMED / UNVERIFIED each)`
- `## 3. Every module the change would touch (file:line, each read)`
- `## 4. Options, with evidence and the bytes each one changes`
- `## 5. Recommendation (precise)`
- `## 6. Risks`
- `## 7. QUESTIONS for the user (numbered, a recommendation each; "all rec" answers them)`
- `## 8. CONFIRMED / UNVERIFIED / NOT DONE`
- `## 9. Left on disk`
- `## USER DECISIONS (<yyyy-mm-dd hh:mm>, binding)` — appended by the orchestrator only, after the user answers.

Current specs:
- `001-audit-and-integration.md` — the full audit and the integration plan.
- `002-llm-openrouter.md` — OpenRouter LLM integration (pending the user's key and model id).
- `003-testing.md` — pytest + Playwright + Camoufox end-to-end proof.
