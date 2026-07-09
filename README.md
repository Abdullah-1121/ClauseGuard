# ClauseGuard

**A reliability-engineered AI agent that reviews contracts against a company playbook — with the evals, tracing, and guardrails that separate a production system from a demo.**

> Status: 🚧 early build. The reliability layer (eval harness, provider abstraction, guardrails) is wired first, on purpose — see [SPEC.md](./SPEC.md).

---

## Why this project exists

Wiring an LLM to "read a contract" is a weekend demo. Making it *dependably* flag the right risks — and being able to prove how often it's right — is the actual engineering problem. ClauseGuard is built around that problem:

- **Evals over vibes.** Detection accuracy is scored against real, human-labeled contract data ([CUAD](https://www.atticusprojectai.org/cuad)) — deterministically, not by asking another LLM if the answer "looks good."
- **Grounded citations by construction.** The LLM judges clauses; it never *locates* them. Citations come from the deterministic segmenter's character offsets, so a hallucinated citation is structurally impossible.
- **Guardrails, not hope.** Schema-validated outputs, citation verification, and a confidence gate that escalates uncertain findings to a human instead of asserting them.
- **Open-source models, swappable providers.** Runs on cloud-hosted open models (Groq) or fully local (Ollama) behind one `LLMProvider` seam — provider choice is config, not code.

## How it works

```
Contract → segment into clauses → classify (cheap model) → match playbook rule
        → evaluate risk (strong model) → guardrail (schema · citation · confidence)
        → ranked findings with rationale, redline, and grounded citation
```

See [SPEC.md](./SPEC.md) for the full architecture, data model, and roadmap.

## Tech stack

Python 3.12 · FastAPI · Pydantic AI (typed agents + structured outputs) · Groq / Ollama (open-source models) · pgvector · Langfuse (tracing seam) · pytest eval harness · GitHub Actions (eval-gated CI) · Docker.

## Quickstart

```bash
cd backend
uv sync                      # installs deps + Python 3.12
cp ../.env.example .env      # add a free GROQ_API_KEY (console.groq.com)

uv run pytest                # full suite runs offline, no key needed
uv run uvicorn app.main:app --reload
```

```bash
# Review a contract
curl -X POST localhost:8000/v1/reviews \
  -H "x-api-key: dev-local-key" -H "content-type: application/json" \
  -d '{"text": "Vendor liability shall be unlimited...", "playbook_id": "vendor_saas_buyer"}'
```

## Evaluation

```bash
uv run python -m evals.runners.run_evals   # needs a provider key; writes evals/reports/
```

The CI pipeline runs lint + type-check + the test/eval-math suite on every push. Headline accuracy numbers (recall / precision on CUAD) land here as the benchmark harness fills in.

## License

MIT — see [LICENSE](./LICENSE). ClauseGuard provides review assistance, **not legal advice**.
