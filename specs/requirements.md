# Eval Harness Requirements

## What We're Building
A deterministic eval harness that measures ClauseGuard's pipeline accuracy against CUAD's human-labeled contract data, producing three headline metrics without LLM-as-judge.

## Inputs
- CUAD dataset (510 contracts, normalized via `cuad_ingest.py`)
- ClauseGuard pipeline (segment → classify → evaluate)
- Playbook (`vendor_saas_buyer.yaml`) with rule-based risk labels

## Outputs
Three metrics, all deterministic:
1. **Classification recall/precision/F1** — did we find the right clause categories?
2. **Citation validity** — does the cited span exist verbatim in source?
3. **Risk-level accuracy** — did we assign the correct risk level?

## Success Criteria
| Metric | Target |
|---|---|
| Risk-clause recall | ≥ 0.85 |
| Precision | ≥ 0.80 |
| Citation validity | 100% (enforced by guardrail) |
| Risk-level accuracy | ≥ 0.75 |
| LLM-vs-rules agreement | tracked, reported |

## Non-Goals
- No human-labeled risk dataset (rule-based labels only for v1)
- No LLM-as-judge for headline metrics (tracked as supplementary metric only)
- No fine-tuning or prompt iteration in this phase
- No frontend for eval results

## Constraints
- All eval metrics computed by Python functions, not LLM calls
- Ambiguous clauses default to deviation (buyer-side conservatism)
- Eval must run in CI without API key for rule-based metrics
- Classification + citation eval requires API key (LLM calls)
- Rule-based risk labeling must be deterministic (same input → same output)
