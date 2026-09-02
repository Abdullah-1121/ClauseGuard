# ClauseGuard

**A reliability-engineered AI agent that reviews a contract against your company playbook — with the evals, tracing, and guardrails that separate a production system from a demo.**

ClauseGuard is an AI-engineering showcase of one idea: *an LLM is a probabilistic judge, and the surrounding system has to make it dependable.* It turns a contract's clauses into ranked, citation-grounded, confidence-scored risk findings — and, when it isn't sure, escalates to a human instead of overclaiming.

> **Status:** MVP complete. The pipeline works end-to-end, the eval harness is validated against real CUAD contract data, 59/59 tests pass, `ruff` and `mypy` are clean, and everything runs on a free-tier LLM key. See [specs/](./specs/) for the engineering record and [AGENTS.md](./AGENTS.md) for the full design process.

---

## Why this project exists

Wiring an LLM to "read a contract" is a weekend demo. Making it *dependably* flag the right risks — and being able to prove how often it's right — is the actual AI-engineering problem. ClauseGuard is built around that problem:

- **Evals over vibes.** Detection accuracy is scored against real, human-labeled contract data ([CUAD](https://www.atticusprojectai.org/cuad)) — deterministically, *not* by asking another LLM whether the answer "looks good."
- **Grounded citations by construction.** The LLM judges clauses; it never *locates* them. Citations come from the deterministic segmenter's character offsets, so a hallucinated citation is structurally impossible — and the guardrail re-verifies the span before anything is emitted.
- **A guardrail stage, not a hope.** Schema-constrained outputs, citation verification, and a confidence gate that escalates uncertain findings to a human.
- **Rate-limit honesty.** A `429` "tokens per day" quota failure raises fast instead of faking a hang; transient per-minute limits back off and retry. Robust vs. broken failure is classified once in `classify.py`.
- **Real files in, real text out.** Upload a digital PDF or Word DOCX and it's parsed to plain text (stdlib for DOCX, `pypdf` for PDF) and fed to the *same* pipeline. Scanned/image-only PDFs and unknown types fail loudly as `415` before any token spend — never silently degraded text that would poison downstream citations.

---

## Architecture

The pipeline is an explicit, readable control flow — deliberately **not** a heavyweight graph framework. Each stage has a single responsibility, and the seams are where the reliability engineering lives.

```
            ┌────────────────────────────────────────────────────────────┐
            │            The pipeline (app/orchestrator/pipeline.py)     │
            └────────────────────────────────────────────────────────────┘

 Contract text ─▶ SEGMENT        deterministic clause splitter + char offsets
                ─▶ CLASSIFY      cheap model → category from the playbook's 12
                ─▶ MATCH RULE    map category to the playbook rule for it
                ─▶ EVALUATE      strong model → status · risk · rationale · redline
                ─▶ GUARDRAIL     verify citation ✓ · confidence gate → human
                ─▶ RANK          sort by risk, then confidence

                     └─▶  { findings: ranked, rationale, redline, citation }
                          { usage: latency }        { traced end-to-end }
```

### Why this shape

**The LLM judges, it never locates.** Division of labor is the core design decision. A hallucinated *citation* is a catastrophic failure for an AI legal reviewer — it points a user at text the model never actually read. So:

- `segment()` (deterministic) splits a contract on blank-line boundaries and records the **exact character offset** of every clause.
- `classify_clause()` / `evaluate_clause()` (LLM) judge *content* and *risk* but receive and return the already-offset clause — they cannot invent a location.
- `verify_citation()` (deterministic) re-checks `source[start:end] == citation.text` before a finding is emitted. If it doesn't match, the finding is silently dropped. Hallucinated citations are not mitigated — they're **impossible by construction**, then double-checked.

This separation is the whole point: it's the difference between "an AI that *might* be hallucinating" and "an AI whose hallucination mode is structurally disabled."

### Stage detail

| Stage | Whence | What it does | Why it matters |
|---|---|---|---|
| **Segment** | `pipeline/parse.py` | Deterministic clause splitter; emits `(text, start, end)` offsets | Grounds citations; the LLM never sees raw offsets |
| **Classify** | `pipeline/classify.py` | Cheap model assigns one of 12 categories (or `other`) with confidence | Cheapest model does the high-volume work; batched for throughput |
| **Match rule** | `playbooks/` | Category → playbook rule (YAML-driven, per-tenant-ish) | Reviewer is playbook-aware, not generic "AI opinion" |
| **Evaluate** | `pipeline/evaluate.py` | Strong model → deviation status, risk level, rationale, suggested redline | Higher-stakes reasoning gets the stronger model |
| **Guardrail** | `pipeline/guardrails.py` | Verify citation span; confidence gate → `needs_human_review` | Pure, deterministic, fully unit-tested safety net |
| **Rank** | `pipeline.py` | Sort findings by risk (then confidence) | The review reads like a triage, not a dump |

Models are swappable behind `providers/factory.py` (Groq, Cerebras, OpenRouter, or local Ollama) — the same pipeline runs on hosted open weights or offline.

---

## Reliability engineering

This is the differentiator. Each decision here exists because a real failure mode was hit, traced, and engineered away.

### 1. Fail loud, never fake a hang or a false zero

A spent free-tier quota and a broken model name must not behave the same. `is_retryable_model_error()` in `classify.py` classifies each HTTP failure:

- **429 `tokens-per-day` (TPD)** → not retryable. The daily allowance resets on a rolling 24h window; no backoff inside one run can fix it. **Fail fast.**
- **429/413 RPM/TPM** → retryable. The window drains in seconds, so back off exponentially (up to ~90s patience).
- **400 `output_parse_failed`** → retryable. An open-weight model occasionally emits an essay instead of JSON on *that generation* only — a quick retry.
- **Anything else (bad model, bad auth)** → **raise**. The eval runner explicitly re-raises: a silent `404` would fake a `0% recall` that hides a broken config, not a bad classifier.

> The debugging gauntlet this came from: a config pointed at a retired model (`llama-3.1-8b-instant`); every call 404'd and the runner silently swallowed it, producing a fake `0/0/0` score. The lesson — *an eval that swalows errors is worse than no eval* — is baked into the design.

### 2. Batch by characters, not clause count

A fixed clause count per batch is a trap. Real contract clauses run to 1,700+ characters; stuffing too many long clauses into one request blows past the model's **output-token ceiling**, the model emits truncated JSON, and Groq fires `output_parse_failed` 400s that loop through retries. `classify_clauses()` caps total batch size at **6,000 chars** *and* clause count at 8 — keeping each request digestible while batching cuts API calls ~15×.

### 3. Free-tier token envelope as a first-class constraint

Groq's free tier is ~200k tokens/day rolling — the real constraint isn't the code, it's the quota. The app handles this gracefully; full benchmarking needs a larger-budget provider (Cerebras) or subset runs. Nothing in the code assumes unlimited tokens.

### 4. Fail-loud file ingestion

`ingest.py` converts an upload to plain text through one seam, `extract_text(data, mime)`, so citations stay offset-valid against *exactly what was reviewed*:

- **Digital PDFs** via `pypdf`; **DOCX** via Python's stdlib (`zipfile` + `xml.etree`) — no `python-docx` dependency.
- DOCX paragraphs have an invisible trap: flattening all `<w:t>` runs silently fuses paragraph boundaries, and the segmenter misses findings. Fix: emit `\n\n` per `<w:p>` so DOCX matches the PDF path's blank-line separator.
- **Scanned PDFs** (no text layer), **corrupt files**, and **unknown types** raise `IngestionError` → HTTP `415` **before any token spend**. The real parse error is logged server-side; the user gets a clean, actionable message — never library English, never silent degradation.
- The upload is always closed via `try/finally`, and the async handler never blocks the event loop.

### 5. Output guardrails are deterministic and unit-tested

`verify_citation()` and `needs_human_review()` are pure functions — no LLM, no randomness — with dedicated tests in `tests/test_guardrails.py`. The probabilistic part of the system is contained; the safety net is not.

---

## Observability (Langfuse)

Every pipeline stage is traced through a `@observe` decorator seam (`app/obs/langfuse.py`): classify, batch-classify, evaluate, and the whole review as an agent trace — capturing inputs, outputs, latency, and the parent/child span tree. Tracing is optional and no-ops when no keys are configured.

> **Honest limitation:** the decorator captures inputs/outputs/latency/trace topology, but **not** raw prompts or token counts under the current setup. Token/cost accounting is a declared future milestone (see [SPEC §9.4](./SPEC.md)).

---

## Evaluation

The eval harness answers the only question that matters: **how often is the reviewer right?** It scores against real human-labeled CUAD data (510 contracts; 467 with playbook-relevant clauses; 2,387 gold labels) — deterministically, never via an LLM judge.

### The metrics

| Metric | What it measures | Formula source |
|---|---|---|
| **Precision** | Of the category labels we flag, how many were truly risky | `TP / (TP + FP)` |
| **Recall** | Of the risky categories a human labeled, how many we caught | `TP / (TP + FN)` |
| **F1** | Harmonic mean of the two | `2·P·R / (P+R)` |
| **Risk accuracy** | Does the LLM's risk level match the rule-based ground truth | `correct / total` |
| **LLM agreement** | Does the LLM's deviation/compliant call match the rule-based label | `agree / total` |

Micro-averaged over contracts (each category label counts once), computed in `evals/metrics.py`, and all three of classification, rule-based risk labeling, and LLM evaluation are exercised by the `--full` runner. Rule-based labeling is the deterministic ground truth — it runs **without an API key**, so the non-LLM half of the harness is free and fully reproducible.

### Running it

```bash
cd backend
cp .env.example .env       # add a free GROQ_API_KEY (console.groq.com)

# Detection eval (recall / precision vs CUAD gold labels on the dev split)
uv run python -m evals.runners.run_detection_eval --split dev --limit 8

# Full eval (adds risk accuracy + LLM-vs-rules agreement)
uv run python -m evals.runners.run_detection_eval --split dev --limit 8 --full
```

Reports (timestamped JSON) land in `backend/evals/reports/`.

### Real numbers (Groq free tier, dev split, 2 contracts / 100 clauses each)

| Metric | Detection only | Full eval |
|---|---|---|
| **Precision** | 0.714 | 0.667 |
| **Recall** | 0.385 | 0.462 |
| **F1** | 0.500 | 0.545 |
| Risk accuracy (rules vs LLM) | — | 0.333 (6/18) |
| LLM agreement (rules vs LLM) | — | 0.722 (13/18) |

**Read these honestly — they are directional, not a benchmark.** The free-tier quota caps any run to a couple of contracts per day; F1 ~0.5 on 100 clauses tells you the hard part (recall on diverse legal prose) is real and unsolved, while a precision ~0.7 says what *is* flagged is mostly correct. The rule-vs-LLM agreement (0.72) is the more stable signal than the tiny risk-accuracy sample (18 clauses). Larger-budget runs are the declared next step, not a finished claim.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language / runtime | Python 3.12 | Natural fit for the LLM + eval ecosystem |
| API | FastAPI + Pydantic v2 | Typed request/response contracts; async throughout |
| Agents / tooling | Pydantic AI | Typed `Agent` objects with schema-constrained structured output |
| Models | Groq / Cerebras / OpenRouter / Ollama (open-weight) | Provider-swappable behind a factory; runs offline-safe |
| Observability | Langfuse (`@observe`) | Industry-standard trace/LLM telemetry |
| Ingestion | `pypdf` + stdlib `zipfile`/`xml.etree` | No heavyweight docx dependency |
| Eval | pytest + `evals/` harness | Deterministic, CUAD-grounded, headless-cheap |
| CI | GitHub Actions | ruff + mypy + pytest on push/PR |

---

## Quickstart

```bash
# Backend
cd backend
cp .env.example .env       # add a free key
uv sync
uv run uvicorn app.main:app --reload

# Frontend (from repo root)
cd frontend
npm install && npm run dev
```

---

## API

Reviews are **async**: `POST` queues a job and returns a `review_id` (HTTP 202);
poll `GET /v1/reviews/{id}` until it reaches `completed` (with `result`) or
`failed` (with `error`). Jobs persist in `clauseguard.db` (SQLite;
`CLAUSEGUARD_DB_PATH`).

**Two ways to run a review:** on the *server's* configured models (needs a valid
`X-API-Key`), or **bring-your-own-key** — send `provider` + `api_key` + `model`
in the body and the review runs on *your* key, your model, *your* quota. BYOK
skips the server key and the daily token budget.

```bash
# Model catalog for the UI (also handy for scripting)
curl localhost:8000/v1/models
# → {"providers": {"groq": {"models": [...]}, "openrouter": {"models": [...]}}}

# BYOK — your key, your model (no X-API-Key needed)
curl -X POST localhost:8000/v1/reviews \
  -H 'Content-Type: application/json' \
  -d '{"text": "1. Limitation of Liability. Vendor liability shall be unlimited.",
       "provider": "groq", "api_key": "<yours>", "model": "llama-3.3-70b-versatile"}'
# → {"review_id": "...", "status": "pending"}

# Server key — runs on the server's configured models
curl -X POST localhost:8000/v1/reviews \
  -H 'X-API-Key: dev-local-key' -H 'Content-Type: application/json' \
  -d '{"text": "1. Limitation of Liability. Vendor liability shall be unlimited."}'

# Queue an uploaded contract (digital PDF or DOCX) — same BYOK field contract,
# sent as multipart form fields
curl -X POST localhost:8000/v1/reviews/file \
  -F 'file=@contract.docx' -F 'provider=groq' -F 'api_key=<yours>' -F 'model=llama-3.3-70b-versatile'

# Poll for the result (open, rate-limited)
curl -X GET localhost:8000/v1/reviews/<review_id>
```

`POST /v1/reviews*` requires **either** a valid `X-API-Key` (server mode) **or**
`provider`/`api_key`/`model` together (BYOK); anything else is `401`, and a
half-filled BYOK combo is `400`. `GET /v1/models`, `GET /v1/playbooks`, and
`GET /v1/reviews/{id}` are open but rate-limited by client IP
(`CLAUSEGUARD_RATE_LIMIT_PER_MINUTE`; in-memory window, default 10, 0 disables).
The frontend stores your key in localStorage and only ever sends it inside one
review POST.

**Spend protection (server mode only):** with BYOK the caller pays, so the
server's daily quota is untouchable by construction. For server-funded runs two
guards protect your provider quota:
- `CLAUSEGUARD_DAILY_TOKEN_BUDGET` — completed server-funded reviews accrue their
  input+output tokens (SQLite `token_budget` table); once the day's total reaches
  the budget, new submissions get `429` until the next UTC day. `0` disables.
- `CLAUSEGUARD_MAX_REVIEW_CHARS` — reject content over N characters before a single
  request can burn the whole budget (default 100k; `0` disables). Applies to both modes.

---

## Deploy

The root `Dockerfile` builds the frontend and backend into **one image** that
serves both the UI and the API. It works on Railway/Fly.io/Render, and is the
canonical path for **Hugging Face Spaces (Docker Space)** — put the repo in a
Space, set the env vars as Space *secrets*, and give it a CPU + a bit of RAM
(the frontend build needs ~2GB to compile).

```bash
# generic
docker build -t clauseguard .
docker run -p 8000:8000 -e GROQ_API_KEY=... -e CLAUSEGUARD_API_KEYS=dev-local-key clauseguard
```

HF Spaces specifics:
- The container listens on `$PORT` (7860 on Spaces; the Dockerfile defaults there too).
- Set `GROQ_API_KEY`, `CLAUSEGUARD_API_KEYS=dev-local-key`, and
  `CLAUSEGUARD_DAILY_TOKEN_BUDGET` (e.g. `20000`) in the Space's Settings → Secrets
  so a public visitor cannot drain your free-tier quota.
- The SQLite job store (`clauseguard.db`) lives on the container's ephemeral disk
  and is wiped on restart — acceptable for a demo; jobs do not survive redeploys.
- Make the Space **private** if it's a portfolio demo — that alone is the
  strongest quota protection and needs no code.

Deploy env vars:
- `GROQ_API_KEY` (or `OPENROUTER_API_KEY`) — used for **server mode** reviews; BYOK callers never touch it.
- `CLAUSEGUARD_API_KEYS` — accepted `X-API-Key` values for server mode (`dev-local-key` by default).
- `CLAUSEGUARD_DAILY_TOKEN_BUDGET` — hard daily token cap, server mode only (see above).
- `CLAUSEGUARD_MAX_REVIEW_CHARS` — per-review content cap (default 100k).
- `CLAUSEGUARD_DB_PATH` — points the SQLite job store somewhere persistent if you want jobs to survive redeploys (default `clauseguard.db` on the container's scratch disk).
- `CLAUSEGUARD_CORS_ORIGINS` — comma-separated origins; only needed if you host the UI separately (set `VITE_API_BASE_URL` on the frontend to match).

The live deployment is a **FastAPI Cloud** service (`fastapi run ./app/main.py`,
which is why `fastapi[standard]` is the pinned dep); the same single-image
Dockerfile is the source for that build.

---

## Engineering record

- **`specs/`** — requirements, design, and execution plan (the spec-driven workflow).
- **`AGENTS.md`** — the full design process: hard-won lessons, architectural decisions, honest limitations.
- **`backend/tests/`** — 59 tests covering the guardrails, metrics math, risk rules, parse/segment, pipeline, file ingestion, HTTP endpoints (auth/404/413/415/rate-limit/budget/BYOK), and the review job store.
- **CI** — `ruff` lint, `mypy` type-check, `pytest` on every push/PR (`continue-on-error` on mypy while types stabilize).

### Notable decisions

- **Rule-based risk labeling** (12 Python rules in one module + a dispatcher, not 12 un-maintainable functions) as the deterministic ground truth; **default-to-deviation** for ambiguous clauses (buyer-side conservatism).
- **A plain async orchestrator** rather than a graph framework — the control flow is 100 lines and readable; a framework would add complexity, not reliability.
- **`--full` flag on the existing runner** instead of a parallel runner — one battle-tested entry point.
- **DOCX via stdlib** and **pypdf only** for ingestion — no `python-docx` dependency; scanned PDFs fail loud, never degrade silently.

---

## Roadmap & known limitations

- Larger-budget eval runs (Cerebras / OpenRouter) to firm up recall/precision beyond the free-tier subset.
- Raw prompt/token accounting in the Langfuse trace (declared; see SPEC §9.4).
- Vector-backed similarity (pgvector) for fuzzy playbook matching is not yet integrated.
- The free tier caps daily benchmarking; plan subset runs per window.

---

## License

MIT — see [LICENSE](./LICENSE). ClauseGuard provides review assistance, **not legal advice**.
