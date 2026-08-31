"""Rule-based risk labeling — deterministic, no LLM calls.

Maps clause text + category to (status, risk_level) using keyword matching.
Used as ground truth for eval metrics when human-labeled risk data is unavailable.

Design: one dict, one function. The dict encodes what the playbook says is
risky vs. acceptable for each category. Ambiguous cases default to deviation
(buyer-side conservatism).
"""

from __future__ import annotations

from app.models.enums import ClauseCategory, FindingStatus, RiskLevel

# Deviation keywords: if ANY appear in the clause text, it's a deviation.
# Compliant keywords: if ANY appear (and no deviation keywords), it's compliant.
# risk: the risk level when it's a deviation.
# Default on ambiguity: deviation (buyer-side conservatism).
RULES: dict[str, dict] = {
    ClauseCategory.CAP_ON_LIABILITY: {
        "deviation": [
            "unlimited", "uncapped", "no limit",
            "sole liability", "aggregate liability shall",
        ],
        "compliant": [
            "12 months", "twelve months", "1 year",
            "fees paid in the", "fees paid during",
        ],
        "risk": RiskLevel.HIGH,
    },
    ClauseCategory.UNCAPPED_LIABILITY: {
        "deviation": ["unlimited", "uncapped", "no limit", "without limitation"],
        "compliant": ["subject to", "limited to", "shall not exceed", "cap on"],
        "risk": RiskLevel.HIGH,
    },
    ClauseCategory.ANTI_ASSIGNMENT: {
        "deviation": [
            "shall not assign", "may not assign",
            "without prior written consent", "prohibited from assigning",
        ],
        "compliant": [
            "affiliate", "merger", "acquisition",
            "successor", "sale of substantially all",
        ],
        "risk": RiskLevel.MEDIUM,
    },
    ClauseCategory.TERMINATION_FOR_CONVENIENCE: {
        "deviation": [
            "no right to terminate", "only for cause",
            "material breach only", "solely upon",
        ],
        "compliant": [
            "30 days", "thirty days", "convenience",
            "without cause", "written notice",
        ],
        "risk": RiskLevel.MEDIUM,
    },
    ClauseCategory.RENEWAL_TERM: {
        "deviation": [
            "automatically renew", "auto-renew",
            "successive", "without notice",
        ],
        "compliant": [
            "written consent", "written notice",
            "opt-out", "30 days notice", "prior written",
        ],
        "risk": RiskLevel.MEDIUM,
    },
    ClauseCategory.GOVERNING_LAW: {
        "deviation": [
            "laws of the united kingdom", "laws of singapore",
            "laws of the european", "governed by the laws of england",
            "governed by french", "governed by german",
        ],
        "compliant": ["delaware", "new york", "california", "state of", "neutral"],
        "risk": RiskLevel.LOW,
    },
    ClauseCategory.NON_COMPETE: {
        "deviation": [
            "shall not compete", "non-compete", "non-solicit",
            "restrict", "shall not engage", "shall not accept",
        ],
        "compliant": [],
        "risk": RiskLevel.HIGH,
    },
    ClauseCategory.EXCLUSIVITY: {
        "deviation": [
            "exclusive", "sole source",
            "shall not obtain from", "exclusivity",
        ],
        "compliant": [],
        "risk": RiskLevel.MEDIUM,
    },
    ClauseCategory.MOST_FAVORED_NATION: {
        "deviation": [
            "most favored", "mfn", "best terms",
            "equal or better", "at least as favorable",
        ],
        "compliant": [],
        "risk": RiskLevel.LOW,
    },
    ClauseCategory.IP_OWNERSHIP_ASSIGNMENT: {
        "deviation": [
            "assigns all", "work for hire", "belongs to vendor",
            "shall vest in", "transfer of ownership", "all right, title",
        ],
        "compliant": [
            "retains ownership", "background ip",
            "deliverables", "intellectual property of",
        ],
        "risk": RiskLevel.HIGH,
    },
    ClauseCategory.AUDIT_RIGHTS: {
        "deviation": [
            "unlimited audit", "at any time",
            "without notice", "at its sole discretion",
        ],
        "compliant": [
            "reasonable notice", "business hours",
            "once per year", "annual", "prior written",
        ],
        "risk": RiskLevel.LOW,
    },
    ClauseCategory.INSURANCE: {
        "deviation": [
            "buyer shall", "at buyer's expense",
            "customer shall", "at its own cost",
        ],
        "compliant": [
            "vendor shall", "provider shall",
            "commercially reasonable", "maintain insurance",
        ],
        "risk": RiskLevel.LOW,
    },
}


def evaluate(text: str, category: str) -> tuple[FindingStatus, RiskLevel]:
    """Evaluate a clause against rule-based risk ground truth.

    Returns (status, risk_level). Both are StrEnum members, so they compare
    equal to their `.value` strings — callers may coerce with `.value` or not.
    """
    rule = RULES.get(category)
    if rule is None:
        return FindingStatus.COMPLIANT, RiskLevel.NONE

    lower = text.lower()

    if any(kw in lower for kw in rule["deviation"]):
        return FindingStatus.DEVIATION, rule["risk"]

    if rule["compliant"] and any(kw in lower for kw in rule["compliant"]):
        return FindingStatus.COMPLIANT, RiskLevel.NONE

    # Ambiguous: default to deviation (buyer-side conservatism)
    return FindingStatus.DEVIATION, rule["risk"]
