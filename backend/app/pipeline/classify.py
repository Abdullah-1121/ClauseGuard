"""Clause classification using the cheap/fast model.

The agent is constrained to the ClassificationOutput schema, so the model can
only return a valid category from our enum. Exposed at module scope so tests can
`classifier_agent.override(model=TestModel())` for deterministic, keyless runs.
"""

from __future__ import annotations

from pydantic_ai import Agent

from app.models.enums import ClauseCategory
from app.models.schemas import ClassificationOutput, Clause
from app.providers.factory import build_model

_CATEGORIES = ", ".join(c.value for c in ClauseCategory)

classifier_agent = Agent(
    build_model("cheap"),
    output_type=ClassificationOutput,
    instructions=(
        "You classify a single contract clause into exactly one category from: "
        f"{_CATEGORIES}. Choose 'other' if none clearly apply. "
        "Return a calibrated confidence between 0 and 1."
    ),
)


async def classify_clause(clause: Clause) -> ClassificationOutput:
    result = await classifier_agent.run(clause.text)
    return result.output
