"""Clause risk evaluation using the strong reasoning model.

Compares a clause against the playbook's standard position and returns a
schema-validated judgement (compliant/deviation, risk level, rationale, and a
suggested redline). Not legal advice — see disclaimer surfaced by the API.
"""

from __future__ import annotations

import asyncio

from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from app.models.schemas import Clause, EvaluationOutput, PlaybookRule
from app.pipeline.classify import is_retryable_model_error
from app.providers.factory import build_model

evaluator_agent = Agent(
    build_model("strong"),
    output_type=EvaluationOutput,
    retries=3,
    instructions=(
        "You are a buyer-side contract review assistant. Compare the given clause "
        "to the buyer's standard position. Decide whether it is COMPLIANT or a "
        "DEVIATION, assign a risk level (high/medium/low/none), give a concise "
        "rationale, and if it deviates propose a redline. Return a calibrated "
        "confidence between 0 and 1. This is assistance, not legal advice."
    ),
)


async def evaluate_clause(clause: Clause, rule: PlaybookRule) -> EvaluationOutput:
    prompt = (
        f"Category: {rule.category.value}\n"
        f"Buyer's standard position: {rule.standard_position}\n\n"
        f"Clause under review:\n{clause.text}"
    )
    delay = 1.0
    for attempt in range(8):
        try:
            result = await evaluator_agent.run(prompt)
            break
        except ModelHTTPError as exc:
            if is_retryable_model_error(exc) and attempt < 7:
                await asyncio.sleep(delay if exc.status_code in (413, 429) else 1.0)
                delay = min(delay * 2, 60.0)
                continue
            raise
    return result.output
