"""Output guardrails — pure, deterministic, fully unit-tested.

These are the safety net that turns a probabilistic model into a dependable
system: no ungrounded citations, and low-confidence findings are escalated to a
human rather than asserted.
"""

from __future__ import annotations

from app.models.schemas import Citation


def verify_citation(source: str, citation: Citation) -> bool:
    """A citation is valid only if its span exists verbatim in the source."""
    if not (0 <= citation.start <= citation.end <= len(source)):
        return False
    return source[citation.start : citation.end] == citation.text


def needs_human_review(confidence: float, threshold: float) -> bool:
    """Flag findings the model is not confident enough to assert on its own."""
    return confidence < threshold
