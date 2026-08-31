"""Review orchestrator — the explicit control flow over the pipeline stages.

Deliberately a plain, readable async function rather than a heavyweight graph
framework: segment -> classify -> match rule -> evaluate -> guardrail -> assemble.
Every reviewed clause is traced. Token/cost accounting is wired at the `span`
seam and expanded in a later milestone (see SPEC §9.4).
"""

from __future__ import annotations

import time

from app.config import Settings, get_settings
from app.models.schemas import (
    Citation,
    Finding,
    Playbook,
    ReviewResult,
    UsageStats,
)
from app.obs.langfuse import observe
from app.obs.logging import span
from app.pipeline.classify import classify_clause
from app.pipeline.evaluate import evaluate_clause
from app.pipeline.guardrails import needs_human_review, verify_citation
from app.pipeline.parse import segment


@observe(name="review", as_type="agent")
async def review_contract(
    text: str, playbook: Playbook, settings: Settings | None = None
) -> ReviewResult:
    settings = settings or get_settings()
    started = time.perf_counter()

    clauses = segment(text)
    findings: list[Finding] = []

    for clause in clauses:
        with span("clause.review", clause_index=clause.index):
            classification = await classify_clause(clause)
            rule = playbook.rule_for(classification.category)
            if rule is None:
                continue  # clause type not covered by this playbook

            evaluation = await evaluate_clause(clause, rule)

            citation = Citation(start=clause.start, end=clause.end, text=clause.text)
            if not verify_citation(text, citation):
                # Guardrail: never emit a finding whose citation is not grounded.
                continue

            confidence = min(classification.confidence, evaluation.confidence)
            findings.append(
                Finding(
                    clause_index=clause.index,
                    category=classification.category,
                    status=evaluation.status,
                    risk_level=evaluation.risk_level,
                    rationale=evaluation.rationale,
                    suggested_redline=evaluation.suggested_redline or rule.preferred_redline,
                    citation=citation,
                    confidence=confidence,
                    needs_human_review=needs_human_review(
                        confidence, settings.confidence_threshold
                    ),
                )
            )

    findings.sort(key=lambda f: (f.risk_level.rank, f.confidence), reverse=True)
    usage = UsageStats(latency_ms=round((time.perf_counter() - started) * 1000, 2))
    return ReviewResult(
        playbook_id=playbook.id,
        clause_count=len(clauses),
        findings=findings,
        usage=usage,
    )
