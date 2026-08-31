# ClauseGuard

**A reliability-engineered AI agent that reviews contracts against a company playbook — with the evals, tracing, and guardrails that separate a production system from a demo.**

> Status: MVP complete. Full pipeline works end-to-end, the eval harness is validated against real CUAD contract data, and everything runs offline-safe on a free-tier LLM key. See [specs/](./specs/) and [AGENTS.md](./AGENTS.md) for architecture and engineering record.

---

## Why this project exists

Wiring an LLM to "read a contract" is a weekend demo. Making it *dependably* flag the right risks — and being able to prove how often it's right — is the actual engineering problem. ClauseGuard is built around that problem:

- **Evals over vibes.** Detection accuracy is scored against real, human-labeled contract data ([CUAD](https://www.atticusprojectai.org/cuad)) — deterministically, not by asking another LLM if the answer "looks good."
- **Grounded citations by construction.** The LLM judges clauses; it never *locates* them. Citations come from the deterministic segmenter's character offsets, so a hallucinated citation is structurally impossible.
- **Guardrails, not hope.** Schema-validated outputs, citation verification, and a confidence gate that escalates uncertain findings to a human instead of asserting them.
- **Rate-limit honesty.** A `429` "tokens per day" quota failure raises fast instead of faking a hang; transient per-minute limits back off and retry. The robust vs. broken distinction is encoded once in `classify.py`.
- **Real files in, real text out.** Upload a digital PDF or Word DOCX and it's parsed to plain text (stdlib for DOCX, `pypdf` for PDF) and fed to the same pipeline. Scanned/image-only PDFs and unknown types fail loudly as `415` before any token spend, never degrading silently.

## How it works

```
Contract → segment into clauses → classify (cheap model) → match playbook rule
        → evaluate risk (strong model) → guardrail (schema · citation · confidence)
        → ranked findings with rationale, redline, and grounded citation
```

See [specs/design.md](./specs/design.md) for the architecture and data contracts.

## Tech stack

Python 3.12 · FastAPI · Pydantic AI (typed agents + structured outputs) · Groq / Ollama (open-source models) · pytest eval harness · GitHub Actions (lint + type-check + tests).

## Evaluation

```bash
cd backend
cp .env.example .env       # add a free GROQ_API_KEY (console.groq.com)

# Detection eval (recall / precision vs CUAD gold labels on the dev split)
uv run python -m evals.runners.run_detection_eval --split dev --limit 8

# Full eval (adds rule-vs-LLM risk accuracy + agreement)
uv run python -m evals.runners.run_detection_eval --split dev --limit 8 --full
```

Real numbers on the Groq free tier (subset): precision ~0.71, recall ~0.39, F1 ~0.50 on detection; rule-vs-LLM risk agreement ~0.72. Reports land in `backend/evals/reports/`. The free tier caps runs to a few contracts per day — see [AGENTS.md](./AGENTS.md) for the honest limits.

## API

```bash
cd backend && uv run uvicorn app.main:app --reload
```

```bash
# Review plain text
curl -X POST localhost:8000/v1/reviews \
  -H 'X-API-Key: dev-local-key' -H 'Content-Type: application/json' \
  -d '{"text": "1. Limitation of Liability. Vendor liability shall be unlimited."}'

# Review an uploaded contract (digital PDF or DOCX)
curl -X POST localhost:8000/v1/reviews/file \
  -H 'X-API-Key: dev-local-key' \
  -F 'file=@contract.docx'
```

## License

MIT — see [LICENSE](./LICENSE). ClauseGuard provides review assistance, **not legal advice**.
