"""Clause classification using the cheap/fast model.

The agent is constrained to the ClassificationOutput schema, so the model can
only return a valid category from our enum. Exposed at module scope so tests can
`classifier_agent.override(model=TestModel())` for deterministic, keyless runs.
"""

from __future__ import annotations

import asyncio

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from app.models.enums import ClauseCategory
from app.models.schemas import ClassificationOutput, Clause, ClauseLabel
from app.providers.factory import build_model

_CATEGORIES = ", ".join(c.value for c in ClauseCategory)

classifier_agent = Agent(
    build_model("cheap"),
    output_type=ClassificationOutput,
    # Open-weight models occasionally emit off-schema output; give the framework
    # room to re-prompt with the validation error until it conforms.
    retries=3,
    instructions=(
        "You classify a single contract clause into exactly one category from: "
        f"{_CATEGORIES}. Choose 'other' if none clearly apply. "
        "Return a calibrated confidence between 0 and 1."
    ),
)


async def classify_clause(clause: Clause) -> ClassificationOutput:
    result = await classifier_agent.run(clause.text)
    return result.output


# ── Batched classification ──────────────────────────────────────────────────
# Classifying one clause per request is too call-heavy for real contracts
# (100+ clauses each). The batch agent labels many clauses in a single request,
# cutting API calls ~15x while keeping per-clause granularity for citations.
batch_classifier_agent = Agent(
    build_model("cheap"),
    output_type=list[ClauseLabel],
    retries=5,
    instructions=(
        "You classify contract clauses. You are given several numbered clauses. "
        "Return exactly one result per clause, echoing its [index], the best "
        f"category from: {_CATEGORIES}, and a confidence 0-1. Use 'other' if none "
        "clearly apply. Do not skip or merge clauses."
    ),
)


async def _classify_batch(
    clauses: list[Clause], max_retries: int = 6
) -> list[ClassificationOutput]:
    """Classify one batch of clauses in a single request; align results by index.

    Handles free-tier rate limits gracefully: on HTTP 429 it backs off and
    retries rather than failing the request.
    """
    numbered = "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(clauses))
    delay = 1.0
    for attempt in range(max_retries):
        try:
            result = await batch_classifier_agent.run(numbered)
            break
        except ModelHTTPError as exc:
            if exc.status_code == 429 and attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            raise
    by_index = {label.index: label for label in result.output}
    out: list[ClassificationOutput] = []
    for i in range(len(clauses)):
        label = by_index.get(i)
        if label is None:
            out.append(ClassificationOutput(category=ClauseCategory.OTHER, confidence=0.0))
        else:
            out.append(ClassificationOutput(category=label.category, confidence=label.confidence))
    return out


async def classify_clauses(
    clauses: list[Clause],
    batch_size: int = 12,
    semaphore: asyncio.Semaphore | None = None,
) -> list[ClassificationOutput]:
    """Classify many clauses using batched requests, run concurrently."""
    batches = [clauses[i : i + batch_size] for i in range(0, len(clauses), batch_size)]

    async def run_batch(batch: list[Clause]) -> list[ClassificationOutput]:
        if semaphore is None:
            return await _classify_batch(batch)
        async with semaphore:
            return await _classify_batch(batch)

    results = await asyncio.gather(*(run_batch(b) for b in batches))
    return [item for batch_result in results for item in batch_result]
