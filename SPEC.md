# ClauseGuard — AI Contract Review Agent
### Technical Specification (v0.1)

> **Working name:** ClauseGuard (placeholder — rename before public launch).
> **Status:** Spec / pre-build.
> **Author:** Muhammad Abdullah.
> **Purpose of this project:** A production-grade, reliability-engineered vertical AI agent, built as a flagship portfolio piece to demonstrate applied-AI / agent-engineering ability for US-remote AI roles at AI-native startups.

---

## 1. Problem & Value Proposition

Legal teams and founders spend hours manually reviewing inbound contracts (NDAs, MSAs, SaaS agreements) against their company's standard positions ("playbook"). The work is repetitive, error-prone, and expensive per hour, yet the rules are largely deterministic: *"liability must be capped," "no auto-renewal without notice," "governing law must be X."*

**ClauseGuard** ingests a contract, segments it into clauses, checks each clause against a configurable playbook of standard positions, and returns **risk-flagged findings** — each with the exact source-text citation, a plain-English rationale, and a suggested redline.

The point of this project is **not** that an LLM can read a contract (everyone can wire that up). The point is that it is **measurably reliable**: it ships with an evaluation harness benchmarked on real, expert-labeled contract data, full request tracing, output guardrails, and cost/latency controls. That reliability layer is the actual deliverable.

---

## 2. Goals & Non-Goals

### Goals (MVP)
- Accept a contract (PDF / DOCX / plain text) and return structured, risk-scored findings.
- Check clauses against a **configurable playbook** (YAML) of ~12 high-value clause categories.
- Every finding includes a **verifiable citation** (a character span that provably exists in the source document).
- **Eval harness** benchmarked against the CUAD dataset, runnable locally and in CI, producing accuracy/precision/recall numbers.
- **Observability**: full trace of every clause, model call, token count, latency, and cost.
- **Guardrails**: schema-validated outputs, citation verification, low-confidence → human-escalation path.
- Deployed, with a web UI that renders the contract with inline highlighted findings.

### Non-Goals (explicitly out of scope for MVP)
- Not legal advice; a disclaimer is shown. It assists review, it does not replace a lawyer.
- No contract *authoring* or negotiation automation.
- No multi-party / multi-document diffing (future work).
- No fine-tuning or model training — we use hosted open-source models as-is.
- No user accounts / multi-tenancy beyond a single API key (future work).

---

## 3. Target User & Primary Use Case

**User:** an in-house counsel, legal ops analyst, or a startup founder reviewing an inbound contract.

**Flow:**
1. User uploads a contract and selects a playbook (e.g. "Vendor SaaS — buyer side").
2. ClauseGuard segments the document into clauses.
3. Each clause is classified and checked against the matching playbook rule.
4. User receives a report: a ranked list of findings (High / Medium / Low risk), each linking to the highlighted clause, with rationale and a suggested redline.
5. Low-confidence items are flagged "needs human review" rather than guessed.

---

## 4. Success Metrics (the resume numbers)

These are what the README leads with. Targets are for the MVP playbook categories on a held-out CUAD split.

| Metric | Definition | Target |
|---|---|---|
| **Risk-clause recall** | Of the risky clauses that exist, how many did we catch? | ≥ 0.85 |
| **Precision** | Of the clauses we flagged, how many were truly risky? | ≥ 0.80 |
| **Citation validity** | Cited span exists verbatim in source (guardrail-enforced) | 100% |
| **Risk-level accuracy** | Correct High/Med/Low bucket among true positives | ≥ 0.75 |
| **Cost / contract** | Mean USD per full contract review | tracked, minimized |
| **P95 latency / contract** | 95th-percentile wall-clock per review | tracked, < 60s |

**Credibility note:** detection metrics (recall/precision) are scored against CUAD's human labels — *deterministic, not LLM-judged*. Only subjective quality (redline usefulness) uses an LLM-as-judge, and that is disclosed. This hybrid keeps the headline numbers honest.

---

## 5. Data: CUAD

**Source:** [CUAD — Contract Understanding Atticus Dataset](https://www.atticusprojectai.org/cuad) (CC BY 4.0). 500+ real commercial contracts, ~13,000 clauses labeled by legal experts across 41 categories.

**How we use it:**
- **Playbook seeding:** map ~12 of CUAD's 41 categories (e.g. *Cap On Liability, Anti-Assignment, Termination For Convenience, Renewal Term, Governing Law, Non-Compete, Uncapped Liability, Most Favored Nation, Exclusivity, IP Ownership Assignment, Audit Rights, Insurance*) to playbook rules with standard positions and risk weights.
- **Eval gold set:** CUAD's span annotations become the ground truth for "did we find the clause, and did we cite the right text?"
- **Train/dev/test discipline:** a fixed, committed split. We iterate prompts on dev, report final numbers on an untouched test split. No peeking.

---

## 6. Model & Inference Layer

**Constraint:** open-source models only, no paid API key. Local inference on the dev machine (CPU-only, 16GB) is too slow for the eval loop, so primary inference is a **free cloud endpoint for open-weight models**.

- **Primary provider:** Groq free tier.
  - **Reasoning model:** Llama 3.3 70B (clause risk evaluation, redline generation).
  - **Cheap/fast model:** Llama 3.1 8B (clause classification, routing).
- **Alternates:** OpenRouter (free model variants), Cerebras, Together.
- **Offline fallback:** local **Ollama** (Qwen 2.5 7B / Llama 3.1 8B) — used for a keyless offline demo, not for eval runs.

**Provider abstraction (design decision worth defending):** all model access goes through a single `LLMProvider` interface (`complete()`, `complete_structured()`), with concrete `GroqProvider`, `OpenRouterProvider`, `OllamaProvider`. Provider + model are chosen by config, never hard-coded. This makes model routing (cheap vs strong), swapping providers, and offline demos trivial, and is testable via a `FakeProvider` for deterministic unit tests.

---

## 7. System Architecture

```
                         ┌─────────────────────────────┐
                         │   Next.js + Tailwind UI      │
                         │  upload · highlighted report │
                         └──────────────┬──────────────┘
                                        │ REST (JSON)
                         ┌──────────────▼──────────────┐
                         │        FastAPI backend       │
                         │  auth · rate limit · routes  │
                         └──────────────┬──────────────┘
                                        │
                 ┌──────────────────────▼──────────────────────┐
                 │             Review Orchestrator              │
                 │   (typed state machine over the pipeline)    │
                 └───┬───────┬───────────┬───────────┬──────────┘
                     │       │           │           │
              ┌──────▼─┐ ┌───▼────┐ ┌────▼─────┐ ┌───▼────────┐
              │ Parse  │ │ Clause │ │ Retrieve │ │  Evaluate  │
              │ &      │ │ Classi-│ │ playbook │ │  risk +    │
              │ Segment│ │ fy     │ │ rule     │ │  redline   │
              └────────┘ └────────┘ └────┬─────┘ └───┬────────┘
                                         │           │
                                   ┌─────▼─────┐ ┌───▼────────┐
                                   │  pgvector │ │ Guardrails │
                                   │ (rules +  │ │ schema ·   │
                                   │ examples) │ │ citation · │
                                   └───────────┘ │ confidence │
                                                 └───┬────────┘
                                                     │
                    ┌────────────────────────────────▼──────────┐
                    │  LLMProvider abstraction (Groq/OR/Ollama)  │
                    └────────────────────────────────────────────┘

   Cross-cutting:  Langfuse tracing  ·  cost/latency metering  ·  structured logging
```

---

## 8. The Agent Pipeline (detailed)

1. **Parse & segment.** Extract text from PDF/DOCX (preserve character offsets for citations). Segment into clauses via structural heuristics (numbered sections, headings) with an LLM fallback for messy documents.
2. **Classify.** For each clause, the cheap model assigns a category (one of the playbook categories, or `OTHER`). Cheap model + strict output schema.
3. **Retrieve.** Look up the matching playbook rule(s) for the clause category (and optionally similar example clauses) from pgvector.
4. **Evaluate.** The reasoning model judges the clause against the standard position → `{compliant | deviation}`, risk level, rationale, and a suggested redline if non-compliant.
5. **Guardrail & assemble.** Validate the output schema; verify the citation span exists verbatim in the source; if model confidence is low, mark `needs_human_review` instead of asserting. Assemble the ranked findings report.

Every step emits a Langfuse span with inputs, outputs, token counts, latency, and cost.

---

## 9. Reliability Engineering (the core deliverable)

### 9.1 Evaluation harness
- **Dataset:** committed CUAD split with gold labels.
- **Runner:** pytest-based (+ optionally Promptfoo for prompt comparisons). One command runs the full suite and emits a JSON + Markdown report.
- **Metrics:** recall, precision, F1 per clause category; risk-level accuracy; citation validity; aggregate cost & latency.
- **Regression gating:** evals run in **CI on every PR**; a drop below thresholds fails the build. This is the headline engineering signal.
- **Versioned results:** each run is stamped with model/provider/prompt version so the README can show "v1 → v2 → v3" improvement.

### 9.2 Observability
- **Langfuse** (self-hostable, open source) traces every review end-to-end: per-clause spans, model calls, tokens, latency, cost.
- Structured JSON logging with a correlation/request id threaded through the pipeline.

### 9.3 Guardrails & failure handling
- **Output schema validation** (Pydantic) on every model response; malformed → bounded retry with repair prompt, then fail-safe.
- **Citation verification:** a finding is rejected if its cited span is not found verbatim in the source (kills hallucinated citations — target 100%).
- **Confidence gating:** low-confidence findings become `needs_human_review`, never silent guesses.
- **Timeouts, retries with backoff, and provider fallback** at the `LLMProvider` layer.

### 9.4 Cost & latency controls
- **Model routing:** cheap 8B for classification, strong 70B only for risk reasoning.
- **Caching:** cache classification/evaluation by clause hash to avoid recomputation across eval runs.
- Cost and latency are **first-class metrics**, surfaced in traces and the eval report.

---

## 10. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | **Python 3.12** (pinned) | Many ML/LLM libs lack 3.14 wheels; 3.12 is stable. |
| API | **FastAPI** + Uvicorn | Async, typed, auto OpenAPI docs. |
| Types/validation | **Pydantic v2** | Schemas double as guardrails. |
| Orchestration | Typed state machine (hand-rolled) or **Pydantic AI** | Explicit control flow, defensible in interviews. |
| Models | **Open-source via Groq** (Llama 3.3 70B / 3.1 8B) | Free, fast, open weights. |
| Vector store | **Postgres + pgvector** | One datastore for rules, examples, results. |
| Observability | **Langfuse** | Open-source LLM tracing. |
| Evals | **pytest** (+ Promptfoo optional) | CI-native, deterministic. |
| Frontend | **Next.js + Tailwind** | Highlighted contract viewer; deploys on Vercel. |
| CI/CD | **GitHub Actions** | Lint, type-check, unit tests, **eval gate**. |
| Deploy | Frontend → Vercel; backend + Postgres → Railway/Fly/Render | Free/low-cost tiers. |
| Containerization | **Docker** + docker-compose | Reproducible local + deploy parity. |

---

## 11. API Design (MVP)

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/v1/reviews` | Upload a contract + playbook id → returns a review id (async). |
| `GET` | `/v1/reviews/{id}` | Poll status / fetch findings report. |
| `GET` | `/v1/playbooks` | List available playbooks. |
| `POST` | `/v1/playbooks` | Create/update a playbook (YAML). |
| `GET` | `/healthz` | Liveness/readiness. |

Auth via API key header; per-key rate limiting. All responses are typed and schema-documented via OpenAPI.

---

## 12. Core Data Model (sketch)

```
Playbook       { id, name, side (buyer/seller), rules[] }
PlaybookRule   { category, standard_position, risk_weight, preferred_redline }
Review         { id, status, playbook_id, doc_meta, created_at, cost, latency }
Finding        { review_id, clause_category, risk_level, status,
                 rationale, suggested_redline, citation{start,end,text},
                 confidence, needs_human_review }
```

---

## 13. Repository Structure

```
clauseguard/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routes
│   │   ├── orchestrator/   # pipeline state machine
│   │   ├── providers/      # LLMProvider + Groq/OpenRouter/Ollama/Fake
│   │   ├── pipeline/       # parse, classify, retrieve, evaluate, guardrails
│   │   ├── playbooks/      # YAML playbooks
│   │   ├── models/         # Pydantic schemas + DB models
│   │   └── obs/            # Langfuse + logging setup
│   ├── evals/
│   │   ├── datasets/       # committed CUAD split
│   │   ├── runners/        # pytest eval harness
│   │   └── reports/        # generated JSON/MD results
│   └── tests/
├── frontend/               # Next.js + Tailwind
├── docker-compose.yml
├── .github/workflows/      # CI incl. eval gate
├── SPEC.md
└── README.md               # the case study
```

---

## 14. Milestones / Roadmap (6–8 weeks, part-time)

| Wk | Milestone | "Done" = |
|---|---|---|
| 1 | Scaffold + CUAD ingestion + playbook v1 + **Langfuse + provider abstraction from day one** | repo runs, traces visible, 1 clause round-trips |
| 2 | Parse → segment → classify pipeline | classification eval baseline exists |
| 3 | Retrieve + evaluate + findings + citations | **first end-to-end eval number** |
| 4 | Guardrails (schema, citation verify, escalation) | citation validity 100%; metrics improve |
| 5 | Cost/latency routing + caching + frontend viewer | UI shows highlighted findings |
| 6 | Deploy + auth + rate limit + **CI eval gate** | live URL; PRs gated on evals |
| 7 | README case study + architecture diagram + demo video | public-ready |
| 8 | **"Reverse-engineer for interview defense" pass** | can explain every decision & failure mode cold |

---

## 15. Testing & CI

- **Unit tests** with a `FakeProvider` (deterministic, no network) for pipeline logic and guardrails.
- **Integration tests** for the API and DB.
- **Eval suite** runs in CI; thresholds gate merges.
- CI stages: lint (ruff) → type-check (mypy) → unit/integration tests → eval gate.

---

## 16. Security & Compliance

- Secrets via env vars / secret manager — **never committed** (lesson carried from prior project: no keys in git).
- Input validation & size limits on uploads; sanitize file parsing.
- API-key auth + rate limiting; CORS locked to the frontend origin.
- Uploaded contracts treated as sensitive: not logged in full, retention policy documented.
- Prominent "not legal advice" disclaimer.

---

## 17. What This Project Demonstrates (for the resume / interview)

- **Reliability engineering for non-deterministic systems** — evals, tracing, guardrails, regression gating. The rare signal.
- **Honest measurement** — deterministic benchmark on real labeled data, not vibes.
- **System design** — clean provider abstraction, model routing, async orchestration, cost/latency awareness.
- **Production plumbing** — auth, rate limiting, CI/CD, Docker, deployment.
- **Domain grounding** — a real business workflow, not a toy.

---

## 18. Future Work (post-MVP, shows roadmap thinking)

- Multi-document / clause-level diffing across contract versions.
- Playbook learning from user accept/reject feedback.
- Multi-tenancy + user accounts.
- Additional contract types and jurisdictions.
- Fine-tuned small model for classification to cut cost/latency further.

---

## 19. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Free-tier rate limits slow eval runs | caching by clause hash; batch; alternate providers |
| LLM hallucinates citations | hard citation-verification guardrail (reject if not verbatim) |
| Eval numbers look weak | iterate prompts on dev split; report honestly; improvement curve is itself the story |
| Scope creep (documented tendency) | MVP scope frozen above; extras go to §18 |
| Python 3.14 dependency breakage | pin Python 3.12 in Docker + venv |
```
