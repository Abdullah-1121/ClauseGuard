# Eval Harness Design

## Architecture

```
CUAD contracts (510)
    ↓
load_contracts(split) → list of {id, text, gold_categories, gold_spans}
    ↓
┌─────────────────────────────────────────────────────┐
│  Stage 1: Classification Eval (needs API key)       │
│  segment → classify → compare to gold_categories   │
│  → precision, recall, F1                            │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Stage 2: Rule-Based Risk Labeling (no API key)     │
│  matched clauses → apply category rules             │
│  → deterministic risk ground truth                  │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Stage 3: Risk Evaluation (needs API key)            │
│  evaluate clause against playbook                   │
│  → compare LLM judgment to rule-based label         │
│  → risk-level accuracy, LLM agreement rate          │
└─────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────┐
│  Stage 4: Citation Validation (no API key)          │
│  compare pipeline citation spans to CUAD spans      │
│  → citation validity %                              │
└─────────────────────────────────────────────────────┘
    ↓
Aggregate report: JSON + Markdown
```

## New Module: `evals/risk_rules.py`

Single module, one function per category. Each function:

```python
def evaluate(text: str) -> tuple[str, str]:
    """Returns (status, risk_level) for a clause in this category."""
```

12 functions, one per playbook category. All use keyword matching — no LLM calls, no external dependencies. Pure Python, trivially testable.

### Rule Design per Category

| Category | Deviation Signals | Compliant Signals | Default |
|---|---|---|---|
| cap_on_liability | "unlimited", "uncapped", "no limit", "sole liability" | "12 months", "twelve months", "1 year", "fees paid" | deviation |
| uncapped_liability | "unlimited", "uncapped", "no limit" | "subject to", "limited to", "cap" | deviation |
| anti_assignment | "shall not assign", "may not assign", "without consent" | "affiliate", "merger", "acquisition", "successor" | deviation |
| termination_for_convenience | "no right to terminate", "only for cause", "material breach only" | "30 days", "notice", "convenience" | deviation |
| renewal_term | "automatically renew", "auto-renew", "successive" | "written consent", "written notice", "opt-out", "30 days notice" | deviation |
| governing_law | "laws of [foreign country]", "Singapore", "UK", "EU" | "Delaware", "New York", "California", "neutral" | deviation |
| non_compete | "shall not compete", "non-compete", "non-solicit", "restrict" | (none — any non-compete is deviation) | deviation |
| exclusivity | "exclusive", "sole source", "shall not obtain from" | (none — any exclusivity is deviation) | deviation |
| most_favored_nation | "MFN", "most favored", "best terms", "equal or better" | (none — MFN on buyer is deviation) | deviation |
| ip_ownership_assignment | "assigns all IP", "work for hire", "belongs to vendor" | "retains ownership", "background IP", "deliverables" | deviation |
| audit_rights | "unlimited audit", "at any time", "without notice" | "reasonable notice", "business hours", "once per year" | deviation |
| insurance | "shall maintain insurance", "at buyer's expense", "buyer shall" | "vendor shall", "commercially reasonable" | deviation |

### Ambiguity Handling

If neither deviation nor compliant keywords match: return `(deviation, risk_level)` where `risk_level` comes from the playbook's `risk_weight`. This is the "default to deviation" rule.

## Eval Runner: `evals/runners/run_full_eval.py`

New runner that executes all four stages:

1. Load CUAD contracts for a given split
2. Run classification eval (segment + classify)
3. Run rule-based risk labeling on matched clauses
4. Run LLM evaluation on matched clauses
5. Compare LLM output to rule-based labels
6. Verify citation spans against CUAD spans
7. Aggregate and report

Produces a JSON report with all metrics, timestamped and model-tagged.

## Data Flow for One Contract

```
CUAD Contract #247:
  text: "1. Liability. Vendor's liability shall be unlimited..."
  gold_categories: ["cap_on_liability", "renewal_term"]

  ↓ Classify
  predicted: ["cap_on_liability", "other"]
  → TP: {cap_on_liability}, FP: {other}, FN: {renewal_term}

  ↓ Rule-based labeling (only for matched TP categories)
  cap_on_liability + "unlimited" → (deviation, high)

  ↓ LLM evaluate
  LLM says: (deviation, high, "Liability is uncapped")
  → Matches rule-based label ✓

  ↓ Citation verify
  CUAD span: characters 45-89
  Pipeline span: characters 45-89
  → Match ✓
```

## Files to Create/Modify

| File | Action | Purpose |
|---|---|---|
| `backend/evals/risk_rules.py` | Create | 12 rule functions + dispatcher |
| `backend/evals/runners/run_full_eval.py` | Create | 4-stage eval runner |
| `backend/evals/metrics.py` | Modify | Add risk-level accuracy computation |
| `backend/evals/risk_rules_test.py` | Create | Unit tests for each rule function |

## What We're NOT Building

- No rule editor UI
- No dynamic rule loading from YAML (rules stay in Python for now)
- No confidence thresholds in rule-based labels (binary: compliant or deviation)
- No span-level risk labeling (risk is per-clause, not per-subspan)
