"""Clause-detection eval against CUAD gold labels.

Measures whether ClauseGuard finds the playbook-relevant clause *types* a lawyer
labeled in each contract. Predicted = the set of our-12 categories the classifier
assigns across a contract's clauses; gold = CUAD's labeled categories. Scored
deterministically (evals.metrics), never by an LLM judge.

Run (first pass, small + cheap):
    uv run python -m evals.runners.run_detection_eval --split dev --limit 8

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

from app.config import get_settings
from app.pipeline.classify import classify_clauses
from app.pipeline.parse import segment
from evals.metrics import aggregate

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
    by_id = {json.loads(line)["id"]: json.loads(line) for line in open(_DATA, encoding="utf-8")}
    return [by_id[i] for i in ids if i in by_id]


async def _predict(text: str, sem: asyncio.Semaphore, max_clauses: int) -> tuple[set[str], int]:
    clauses = [c for c in segment(text) if len(c.text) >= MIN_CLAUSE_LEN][:max_clauses]
    # Batched classification: ~15x fewer requests than one call per clause.
    # One retry after a pause so a transient rate-limit doesn't lose a contract.
    for attempt in range(2):
        try:
            labels = await classify_clauses(clauses, batch_size=12, semaphore=sem)
            predicted = {label.category.value for label in labels if label.category != "other"}
            return predicted, len(clauses)
        except Exception:
            if attempt == 0:
                await asyncio.sleep(10)
    return set(), len(clauses)


async def run(split: str, limit: int | None, concurrency: int, max_clauses: int) -> dict:
    contracts = _load_contracts(split, limit)
    sem = asyncio.Semaphore(concurrency)
    pairs: list[tuple[set[str], set[str]]] = []
    started = time.perf_counter()

    for i, contract in enumerate(contracts, 1):
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

    metrics = aggregate(pairs)
    settings = get_settings()
    metrics.update(
        split=split,
        contracts=len(contracts),
        max_clauses=max_clauses,
        provider=settings.provider,
        model_cheap=settings.model_cheap,
        elapsed_s=round(time.perf_counter() - started, 1),
        timestamp=datetime.now(UTC).isoformat(),
    )
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    ap.add_argument("--limit", type=int, default=8, help="max contracts (0 = all)")
    ap.add_argument("--concurrency", type=int, default=5)
    ap.add_argument("--max-clauses", type=int, default=200, help="cap clauses per contract")
    args = ap.parse_args()

    metrics = asyncio.run(
        run(args.split, args.limit or None, args.concurrency, args.max_clauses)
    )
    _REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (_REPORTS / f"detection-{args.split}-{stamp}.json").write_text(json.dumps(metrics, indent=2))
    print("\n" + json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
