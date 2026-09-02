"""Review orchestrator — the explicit control flow over the pipeline stages.

Deliberately a plain, readable async function rather than a heavyweight graph
framework: segment -> classify -> match rule -> evaluate -> guardrail -> assemble.
Every reviewed clause is traced; token/cost usage from both model calls is
accumulated into the returned `UsageStats`. Cost is only filled when the model
back-end reports a price (pydantic-ai knows Groq/Cerebras pricing); otherwise
it stays 0 with the token counts still accurate.
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
    input_tokens = output_tokens = 0
    estimated_cost_usd = 0.0

    for clause in clauses:
        with span("clause.review", clause_index=clause.index):
            classification, classify_usage = await classify_clause(clause)
            input_tokens += classify_usage.input_tokens
            output_tokens += classify_usage.output_tokens
            estimated_cost_usd += classify_usage.cost or 0.0
            rule = playbook.rule_for(classification.category)
            if rule is None:
                continue  # clause type not covered by this playbook

            evaluation, evaluate_usage = await evaluate_clause(clause, rule)
            input_tokens += evaluate_usage.input_tokens
            output_tokens += evaluate_usage.output_tokens
            estimated_cost_usd += evaluate_usage.cost or 0.0

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
    usage = UsageStats(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(estimated_cost_usd, 6),
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return ReviewResult(
        playbook_id=playbook.id,
        clause_count=len(clauses),
        findings=findings,
        usage=usage,
    )
