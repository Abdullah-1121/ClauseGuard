"""Clause-detection eval against CUAD gold labels.

Measures whether ClauseGuard finds the playbook-relevant clause *types* a lawyer
labeled in each contract. Predicted = the set of our-12 categories the classifier
assigns across a contract's clauses; gold = CUAD's labeled categories. Scored
deterministically (evals.metrics), never by an LLM judge.

Run (first pass, small + cheap):
    uv run python -m evals.runners.run_detection_eval --split dev --limit 8

Run full eval (classification + risk + LLM agreement):
    uv run python -m evals.runners.run_detection_eval --split dev --limit 8 --full

Rate-limit friendly: bounded concurrency + exponential backoff, and an optional
per-contract clause cap so a first pass doesn't fan out to tens of thousands of
calls. Drop --limit / raise --max-clauses for the full benchmark.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

import structlog
from pydantic_ai.exceptions import ModelHTTPError

from app.config import get_settings
from app.pipeline.classify import classify_clauses, is_retryable_model_error
from app.pipeline.evaluate import evaluate_clause
from app.pipeline.parse import segment
from app.playbooks.loader import load_playbook
from evals.metrics import aggregate, llm_agreement, risk_accuracy
from evals.risk_rules import evaluate as rule_evaluate

# Silence per-clause span logs so eval progress is readable.
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))

# Segments shorter than this are page numbers / stray fragments, not clauses.
MIN_CLAUSE_LEN = 40

_DATA = Path(__file__).parents[1] / "datasets" / "cuad" / "contracts.jsonl"
_SPLITS = Path(__file__).parents[1] / "splits"
_REPORTS = Path(__file__).parents[1] / "reports"


def _load_contracts(split: str, limit: int | None) -> list[dict]:
    ids = [
        line.strip()
        for line in (_SPLITS / f"{split}.txt").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if limit:
        ids = ids[:limit]
    by_id = {
        json.loads(line)["id"]: json.loads(line) for line in open(_DATA, encoding="utf-8")
    }
    missing = [i for i in ids if i not in by_id]
    if missing:
        print(f"  WARNING: split references {len(missing)} ids missing from dataset:", flush=True)
        for i in missing:
            print(f"    - {i}", flush=True)
    return [by_id[i] for i in ids if i in by_id]


async def _predict(text: str, sem: asyncio.Semaphore, max_clauses: int) -> tuple[set[str], int]:
    clauses = [c for c in segment(text) if len(c.text) >= MIN_CLAUSE_LEN][:max_clauses]
    # Batched classification: ~15x fewer requests than one call per clause.
    # Retry once on a transient rate limit so a busy free tier doesn't drop a
    # contract. Everything else (bad model name, auth) must fail loudly — a
    # silent 404 would fake a 0% recall that hides a broken config, not a bad
    # classifier. `classify_clauses` already backs off on 429 internally.
    try:
        labels = await classify_clauses(clauses, batch_size=8, semaphore=sem)
        predicted = {label.category.value for label in labels if label.category != "other"}
        return predicted, len(clauses)
    except ModelHTTPError as exc:
        # Only transient limits (RPM/TPM/parse) earn a single retry; a spent
        # daily quota (TPD) won't recover inside one run, so it must fail loud.
        if is_retryable_model_error(exc):
            await asyncio.sleep(10)
            labels = await classify_clauses(clauses, batch_size=8, semaphore=sem)
            predicted = {
                label.category.value for label in labels if label.category != "other"
            }
            return predicted, len(clauses)
        raise


async def _predict_full(
    text: str, sem: asyncio.Semaphore, max_clauses: int, playbook
) -> tuple[set[str], list[dict], int]:
    """Classification + rule-based risk labeling + LLM evaluation."""
    clauses = [c for c in segment(text) if len(c.text) >= MIN_CLAUSE_LEN][:max_clauses]
    try:
        labels = await classify_clauses(clauses, batch_size=8, semaphore=sem)
    except ModelHTTPError as exc:
        if not is_retryable_model_error(exc):
            raise
        await asyncio.sleep(10)
        labels = await classify_clauses(clauses, batch_size=8, semaphore=sem)

    predicted = set()
    clause_details = []
    for clause, label in zip(clauses, labels, strict=False):
        if label.category == "other":
            continue
        predicted.add(label.category.value)

        rule = playbook.rule_for(label.category)
        if rule is None:
            continue

        # Rule-based risk ground truth
        rule_status, rule_risk = rule_evaluate(clause.text, label.category.value)

        # LLM evaluation
        llm_eval, _ = await evaluate_clause(clause, rule)

        clause_details.append({
            "category": label.category.value,
            "rule_status": rule_status,
            "rule_risk": rule_risk,
            "llm_status": llm_eval.status.value,
            "llm_risk": llm_eval.risk_level.value,
        })

    return predicted, clause_details, len(clauses)


async def run(
    split: str, limit: int | None, concurrency: int, max_clauses: int, full: bool = False,
) -> dict:
    contracts = _load_contracts(split, limit)
    sem = asyncio.Semaphore(concurrency)
    pairs: list[tuple[set[str], set[str]]] = []
    risk_pairs: list[tuple[str, str]] = []
    agreement_pairs: list[tuple[str, str]] = []
    started = time.perf_counter()

    playbook = load_playbook("vendor_saas_buyer") if full else None

    for i, contract in enumerate(contracts, 1):
        if full:
            predicted, details, n_clauses = await _predict_full(
                contract["text"], sem, max_clauses, playbook
            )
            for d in details:
                risk_pairs.append((d["llm_risk"], d["rule_risk"]))
                agreement_pairs.append((d["llm_status"], d["rule_status"]))
        else:
            predicted, n_clauses = await _predict(contract["text"], sem, max_clauses)

        gold = set(contract["gold_categories"])
        pairs.append((predicted, gold))
        fp = sorted(predicted - gold)
        miss = sorted(gold - predicted)
        print(
            f"[{i}/{len(contracts)}] {contract['id'][:38]:40} "
            f"clauses={n_clauses:4}  false+={fp}  missed={miss}",
            flush=True,
        )

    settings = get_settings()
    metrics = {
        **aggregate(pairs),
        **(risk_accuracy(risk_pairs) if full and risk_pairs else {}),
        **(llm_agreement(agreement_pairs) if full and risk_pairs else {}),
        "split": split,
        "contracts": len(contracts),
        "max_clauses": max_clauses,
        "provider": settings.provider,
        "model_cheap": settings.model_cheap,
        "model_strong": settings.model_strong if full else "",
        "elapsed_s": round(time.perf_counter() - started, 1),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    ap.add_argument("--limit", type=int, default=8, help="max contracts (0 = all)")
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--max-clauses", type=int, default=200, help="cap clauses per contract")
    ap.add_argument("--full", action="store_true", help="run full eval (classify + risk + LLM)")
    args = ap.parse_args()

    metrics = asyncio.run(
        run(args.split, args.limit or None, args.concurrency, args.max_clauses, args.full)
    )
    _REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    prefix = "full-eval" if args.full else "detection"
    (_REPORTS / f"{prefix}-{args.split}-{stamp}.json").write_text(json.dumps(metrics, indent=2))
    print("\n" + json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
