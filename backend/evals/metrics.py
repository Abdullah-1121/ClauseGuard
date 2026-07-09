"""Detection metrics for contract review.

Scored against gold labels (deterministic), not an LLM judge — this is what
keeps the headline recall/precision numbers honest (SPEC §4). A prediction is
the set of clause categories the agent flagged as deviations for a document;
the gold set is the categories a human labeled as risky.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0


def counts_for(predicted: set[str], gold: set[str]) -> Counts:
    return Counts(
        tp=len(predicted & gold),
        fp=len(predicted - gold),
        fn=len(gold - predicted),
    )


def aggregate(pairs: list[tuple[set[str], set[str]]]) -> dict[str, float]:
    """Micro-averaged precision / recall / F1 over (predicted, gold) pairs."""
    total = Counts()
    for predicted, gold in pairs:
        c = counts_for(predicted, gold)
        total.tp += c.tp
        total.fp += c.fp
        total.fn += c.fn

    precision = total.tp / (total.tp + total.fp) if (total.tp + total.fp) else 0.0
    recall = total.tp / (total.tp + total.fn) if (total.tp + total.fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": total.tp,
        "fp": total.fp,
        "fn": total.fn,
    }
