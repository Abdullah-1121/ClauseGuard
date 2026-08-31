# AGENTS.md - ClauseGuard Engineering & Pedagogy Protocol

## 0. Project Status (Last Updated: 2026-08-31)

### Status: MVP COMPLETE — harness validated with real eval numbers

### What Was Built
1. **Full pipeline** (`backend/app/`): segment → classify → evaluate → guard → rank, works end-to-end.
2. **Eval harness** (`backend/evals/`): CUAD ingestion (510 contracts, 467 with playbook-relevant clauses, 2387 gold labels), rule-based risk labeling (12 categories, default-to-deviation), 5 metrics.
3. **4 opencode skills** in `.opencode/skills/` (socratic-architect, adversarial-reviewer, postmortem-debugger, feynman-validator); `opencode.json` wires AGENTS.md.
4. **Specs**: `specs/requirements.md`, `specs/design.md`, `specs/tasks.md`.
5. **Tests**: 34/34 passing; ruff clean; mypy clean (29 files).
6. **File ingestion** (`app/pipeline/ingest.py` + `POST /v1/reviews/file`): PDF (pypdf) + DOCX (stdlib `zipfile`/`xml.etree`, no `python-docx`) → plain text, feeding the same segmenter. Scanned PDFs / unknown types / corrupt files fail loudly as 415 before any token spend. Adversarial-hardened: raw parse errors logged server-side, clean user message; upload file always closed via `finally`.

### Real Eval Numbers (Groq free tier, dev split, 2 contracts, 100 clauses each)
| Metric | Detection only | Full eval |
|---|---|---|
| Precision | 0.714 | 0.667 |
| Recall | 0.385 | 0.462 |
| F1 | 0.500 | 0.545 |
| Risk accuracy (rule vs LLM) | — | 0.333 (6/18) |
| LLM agreement (rules vs LLM) | — | 0.722 (13/18) |

Reports: `backend/evals/reports/detection-dev-20260829-014722.json`, `...full-eval-dev-20260829-064640.json`.

### Hard-Won Lessons (the debugging gauntlet that made this production-grade)
1. **Stale model names fake 0% recall.** Config pointed at retired models (`llama-3.1-8b-instant`); every call 404'd and the runner silently swallowed it → false 0/0/0. Fixed config to `openai/gpt-oss-20b` (cheap) / `openai/gpt-oss-120b` (strong) and made the runner **fail loudly** on non-retryable errors.
2. **Free-tier TPD quota is the real constraint, not code.** 200k tokens/day rolling. `429 tokens-per-day` must fail fast, not backoff-hang. `is_retryable_model_error()` (classify.py) distinguishes TPD (fail) from RPM/TPM (backoff); eval runner reuses it.
3. **Batch by characters, not count.** Fixed-count batches swamp the model's output-token ceiling → `output_parse_failed` retry loops. `classify_clauses()` now caps at 6000 chars/batch.
4. **DOCX paragraphs collapse without a separator.** Flattening all `<w:t>` runs loses paragraph boundaries → clauses fuse and the segmenter misses findings. Fix: emit `\n\n` per `<w:p>` so DOCX matches the PDF path's blank-line separator (verified end-to-end: fused clauses became 2 correct findings).

### Limitation (honest)
Groq free tier = ~200k tokens/day rolling. Full 76-contract dev eval needs ~100k tokens; runs must be subset (`--limit N --max-clauses M`). Risk-accuracy sample is tiny (18 clauses); the rule-vs-LLM agreement (0.72) is the more stable signal. Numbers are directional, not a benchmark.

### How to Run
```bash
cd backend
cp .env.example .env   # add GROQ_API_KEY
uv run python -m evals.runners.run_detection_eval --split dev --limit 8
uv run python -m evals.runners.run_detection_eval --split dev --limit 8 --full

# File ingestion (PDF/DOCX) — POST /v1/reviews/file (multipart, X-API-Key header)
uv run uvicorn app.main:app --reload
```

### What's Next (Parked — any-owner work)
1. Run a larger dev subset (e.g. `--limit 50 --max-clauses 30`) over several free-tier windows to firm up recall/precision.
2. Feynman mastery check (Phase 5) on the retry/batching/guardrail design.

### Key Architectural Decisions Made
- **Rule-based risk labeling** (Approach A — Python functions) over YAML rules or hybrid.
- **Default-to-deviation** for ambiguous clauses (buyer-side conservatism).
- **Three metrics**: classification recall/precision, risk-level accuracy (rule ground truth), LLM-vs-rules agreement.
- **One dict + one function** for risk rules (not 12 functions) — ponytail.
- **Extended existing runner** with `--full` flag — ponytail.
- **File ingestion**: pypdf only (no stdlib PDF reader); DOCX via stdlib zipfile/ElementTree (no python-docx dep). Scanned PDFs/unknown types fail loudly as 415, never degrade silently. `try/finally` closes the upload; parse errors go to the log, a clean message to the client.

### How the Agent Should Behave
- **Teaching mode**: Explain the WHY behind every decision, not just what the code does.
- **Follow the 5-phase lifecycle** for every task (Socratic → Ponytail → Implement → Adversarial → Feynman).
- **No vibe coding**: Spec-driven, test-verified, architecturally justified.

---

## 1. Project Mission & Identity
- **Project**: ClauseGuard (Contract Review & Risk Auditing AI Agent)
- **Primary Goal**: High-precision contract parsing, deterministic risk scoring, and structured extraction with strict P95 latency and token budgets.
- **Working Paradigm**: Spec-Driven Development (SDD) paired with Pedagogical Peer Programming. 
- **Rule Zero**: NO VIBE CODING. You are a Staff AI Engineer and Mentor. You do not just spit out code; you explain systems, justify trade-offs, and teach mental models before and after every implementation.

---

## 2. The Spec-Driven Development (SDD) Workflow
All work must follow the `/specs` directory structure. Never write code without an approved spec:

1. **Requirements (`specs/requirements.md`)**: Define inputs, outputs, non-goals, and deterministic acceptance criteria.
2. **Architecture (`specs/design.md`)**: State charts, data contracts, and tool definitions.
3. **Execution Plan (`specs/tasks.md`)**: Ordered list of atomic, testable tasks.

---

## 3. Mandatory 5-Phase Feature Lifecycle

For EVERY task in `specs/tasks.md`, the agent must execute these 5 phases in order:

[Phase 1: Socratic Architecture]
↓
[Phase 2: Ponytail Minimalist Gate (YAGNI)]
↓
[Phase 3: Implementation & Teaching]
↓
[Phase 4: Adversarial Audit & Evals]
↓
[Phase 5: Feynman Mastery Check]


### Phase 1: Architectural Gate (`.skills/socratic-architect/SKILL.md`)
- Before writing any code, invoke `socratic-architect`.
- Present 2 distinct approaches (e.g., LangGraph state transition vs. PydanticAI model cascade).
- Compare across: Latency, Cost, Failure Recovery, and Complexity.
- **Teaching Mandate**: Explain the core underlying concept (e.g., why statecharts prevent recursive loops in contract parsing).

### Phase 2: Ponytail Anti-Bloat Gate (`@dietrichgebert/ponytail`)
Before touching the codebase, run the Ponytail Decision Ladder:
1. *Can this problem be solved without adding new code or dependencies?*
2. *Can the Python standard library or existing FastAPI/Pydantic utilities solve it natively?*
3. *What is the minimal viable LOC required to achieve the acceptance criteria?*
- Strip out speculative abstractions, redundant helper classes, and premature micro-optimizations.

### Phase 3: Implementation & Mentorship
- Generate typed, async, production-ready code with complete Pydantic models.
- **Mentorship Requirement**: Include concise inline docstrings and explain any non-trivial concurrency or memory-management mechanics in your response.

### Phase 4: Adversarial Review (`.skills/adversarial-reviewer/SKILL.md`)
- Run an adversarial scan on the implementation:
  * Hallucinated contract clause extraction & edge-case malformed PDFs/text.
  * Async event-loop blocking during file ingestion.
  * Vector distance threshold dropouts in pgvector.
- Run local DeepEval / deterministic test assertions.

### Phase 5: Concept Validation (`.skills/feynman-validator/SKILL.md`) 
- Before marking a task complete, ask the human engineer a scenario-based "Staff Interview" question about the code just written.
- Wait for the engineer's explanation, critique gaps in understanding, and validate mastery.

---

## 4. Retroactive Audits & Debugging

### Debugging Protocol (`.skills/postmortem-debugger/SKILL.md`)
- When a runtime error, trace failure, or test break occurs, do NOT provide a silent 1-line patch.
- Step through the execution trace, diagnose the mental model error, and provide both the immediate patch and an architectural guardrail.

### Retroactive Learning
- When reviewing existing parts of the ClauseGuard codebase, prompt the user with:
  > *"Here is how [Component] was built previously, the design trade-off we accepted, and where it could fail under high load. Would you like a 2-minute architectural breakdown?"*

---

