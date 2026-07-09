"""Clause risk evaluation using the strong reasoning model.

Compares a clause against the playbook's standard position and returns a
schema-validated judgement (compliant/deviation, risk level, rationale, and a
suggested redline). Not legal advice — see disclaimer surfaced by the API.
"""

from __future__ import annotations

from pydantic_ai import Agent

from app.models.schemas import Clause, EvaluationOutput, PlaybookRule
from app.providers.factory import build_model

evaluator_agent = Agent(
    build_model("strong"),
    output_type=EvaluationOutput,
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
    result = await evaluator_agent.run(prompt)
    return result.output
