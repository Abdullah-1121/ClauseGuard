# Eval Harness — Execution Plan

## Tasks (ordered, dependent)

### Task 1: Rule-Based Risk Labeler
**Files:** `backend/evals/risk_rules.py`
**What:** 12 functions (one per category) + dispatcher function. Each returns `(status, risk_level)`. Keyword matching only, no LLM.
**Test:** Unit tests for each function — known inputs with expected outputs. Test ambiguous inputs default to deviation.
**Done when:** `pytest backend/evals/risk_rules_test.py` passes.

### Task 2: Extend Metrics Module
**Files:** `backend/evals/metrics.py`
**What:** Add `risk_accuracy(predicted_risks, gold_risks)` function. Computes accuracy of risk-level assignment (high/medium/low/none) given predicted and gold risk labels.
**Test:** Unit test with perfect scores, mixed scores, all-wrong scores.
**Done when:** `pytest backend/evals/test_metrics.py` passes with new test cases.

### Task 3: Full Eval Runner
**Files:** `backend/evals/runners/run_full_eval.py`
**What:** 4-stage runner: classify → rule-label → evaluate → cite-verify. Loads CUAD contracts, runs pipeline, computes all metrics, writes JSON report.
**Test:** Run against 2-3 sample contracts offline to verify wiring. Run against 8 CUAD dev contracts with API key to verify end-to-end.
**Done when:** `uv run python -m evals.runners.run_full_eval --split dev --limit 8` produces a valid JSON report.

### Task 4: CUAD Data Ingest
**Files:** `backend/evals/cuad_ingest.py` (already exists)
**What:** Run the ingest script to download and normalize the full CUAD dataset. Produces `evals/datasets/cuad/contracts.jsonl` and split files.
**Test:** Verify file exists, has 510 contracts, splits are correct.
**Done when:** `uv run python -m evals.cuad_ingest` completes and `contracts.jsonl` has 510 entries.

### Task 5: Run Full Eval on Dev Split
**What:** Execute the full eval on CUAD dev split (76 contracts). Produce headline metrics.
**Done when:** Report shows recall ≥ 0.85, precision ≥ 0.80, citation validity 100%.

### Task 6: CI Integration
**Files:** `.github/workflows/ci.yml`
**What:** Add rule-based risk labeler tests to CI (no API key needed). Classification eval stays local-only (needs API key).
**Done when:** CI passes with new test cases.
