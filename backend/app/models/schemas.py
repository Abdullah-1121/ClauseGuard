"""Domain + LLM I/O schemas.

Design note (defensible decision): the LLM never produces citations. Citations
are derived from the deterministic segmenter's character offsets, so a finding
can only ever cite text that provably exists in the source document. The LLM's
job is limited to *judging* a clause, not *locating* it — which is why our
citation-validity target is 100% by construction, not by hope.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import ClauseCategory, FindingStatus, RiskLevel


# ── Parsing ────────────────────────────────────────────────────────────────
class Clause(BaseModel):
    """A segmented clause with the character offsets it occupies in the source."""

    index: int
    text: str
    start: int
    end: int


# ── LLM output schemas (what the models are constrained to return) ──────────
class ClassificationOutput(BaseModel):
    category: ClauseCategory
    confidence: float = Field(ge=0.0, le=1.0)


class ClauseLabel(BaseModel):
    """One clause's classification within a batched request, keyed by position."""

    index: int
    category: ClauseCategory
    confidence: float = Field(ge=0.0, le=1.0)


class EvaluationOutput(BaseModel):
    status: FindingStatus
    risk_level: RiskLevel
    rationale: str
    suggested_redline: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


# ── Playbook ────────────────────────────────────────────────────────────────
class PlaybookRule(BaseModel):
    category: ClauseCategory
    standard_position: str
    risk_weight: RiskLevel = RiskLevel.MEDIUM
    preferred_redline: str | None = None


class Playbook(BaseModel):
    id: str
    name: str
    side: str = "buyer"
    rules: list[PlaybookRule]

    def rule_for(self, category: ClauseCategory) -> PlaybookRule | None:
        for rule in self.rules:
            if rule.category == category:
                return rule
        return None


# ── Findings / results ──────────────────────────────────────────────────────
class Citation(BaseModel):
    start: int
    end: int
    text: str


class Finding(BaseModel):
    clause_index: int
    category: ClauseCategory
    status: FindingStatus
    risk_level: RiskLevel
    rationale: str
    suggested_redline: str | None = None
    citation: Citation
    confidence: float
    needs_human_review: bool = False


class UsageStats(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0


class ReviewRequest(BaseModel):
    text: str
    playbook_id: str = "vendor_saas_buyer"
    # Bring-your-own-key: when all three are set, the review runs on the
    # caller's provider key + model and skips the server X-API-Key / budget.
    provider: str | None = None
    api_key: str | None = None
    model: str | None = None


class ReviewResult(BaseModel):
    playbook_id: str
    clause_count: int
    findings: list[Finding]
    usage: UsageStats

    @property
    def deviations(self) -> list[Finding]:
        return [f for f in self.findings if f.status == FindingStatus.DEVIATION]
