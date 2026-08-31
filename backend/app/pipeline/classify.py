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


def is_retryable_model_error(exc: ModelHTTPError) -> bool:
    """True for transient failures worth a retry, not config/auth bugs.

    Rate limits that reset in seconds (RPM) are worth backing off for. A
    consumed daily allowance (TPD) resets over a rolling 24h window — no
    backoff inside one run fixes that, so it must fail fast, not fake-hang.
    Open-weight reasoning models occasionally emit an essay instead of the
    requested JSON, which Groq rejects with 400 `output_parse_failed` on that
    generation only.
    """
    if exc.status_code == 429 and isinstance(exc.body, dict):
        msg = exc.body.get("error", {}).get("message", "")
        if "tokens per day" in msg:
            return False  # daily quota spent; retrying can't help this run
    if exc.status_code in (413, 429):
        return True
    if exc.status_code == 400 and isinstance(exc.body, dict):
        return exc.body.get("error", {}).get("code") == "output_parse_failed"
    return False


async def _classify_batch(
    clauses: list[Clause], max_retries: int = 8
) -> list[ClassificationOutput]:
    """Classify one batch of clauses in a single request; align results by index.

    Handles free-tier rate limits gracefully: on HTTP 429 (RPM) and 413
    (`rate_limit_exceeded`, TPM) it backs off and retries rather than failing.
    Backoff patience (~90s) exceeds a TPM window so a rolling quota can drain.
    Output-parse failures retry on a 1s cadence (flaky, not quota-bound).
    """
    numbered = "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(clauses))
    delay = 1.0
    for attempt in range(max_retries):
        try:
            result = await batch_classifier_agent.run(numbered)
            break
        except ModelHTTPError as exc:
            if is_retryable_model_error(exc) and attempt < max_retries - 1:
                # Rate limits wait out the window (exponential); a failed JSON
                # generation is just bowl-flush luck and retries immediately.
                await asyncio.sleep(delay if exc.status_code in (413, 429) else 1.0)
                delay = min(delay * 2, 60.0)
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
    batch_size: int = 8,
    max_batch_chars: int = 6000,
    semaphore: asyncio.Semaphore | None = None,
) -> list[ClassificationOutput]:
    """Classify many clauses using batched requests, run concurrently.

    Batches are capped by *characters*, not just clause count. A fixed clause
    count is a trap: a batch of long real contract clauses (some 1,700+ chars)
    blows past the model's output-token ceiling, the model emits truncated JSON,
    and Groq fires `output_parse_failed` 400s that loop through retries. Capping
    total batch size (default 6,000 chars) keeps each request digestible while
    batch_size (default 8) still bounds the clause count.
    """
    batches: list[list[Clause]] = []
    cur: list[Clause] = []
    cur_chars = 0
    for clause in clauses:
        nxt = cur_chars + len(clause.text)
        if cur and (nxt > max_batch_chars or len(cur) >= batch_size):
            batches.append(cur)
            cur, cur_chars = [], 0
        cur.append(clause)
        cur_chars += len(clause.text)
    if cur:
        batches.append(cur)

    async def run_batch(batch: list[Clause]) -> list[ClassificationOutput]:
        if semaphore is None:
            return await _classify_batch(batch)
        async with semaphore:
            return await _classify_batch(batch)

    results = await asyncio.gather(*(run_batch(b) for b in batches))
    return [item for batch_result in results for item in batch_result]
