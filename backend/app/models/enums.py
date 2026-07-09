"""Enumerations for clause categories, risk, and finding status.

Clause categories are a curated subset of the 41 CUAD categories — the ~12
highest-value ones for a buyer-side review. Kept as an enum so both the LLM
output schema and the playbook are constrained to the same vocabulary.
"""

from __future__ import annotations

from enum import StrEnum


class ClauseCategory(StrEnum):
    CAP_ON_LIABILITY = "cap_on_liability"
    UNCAPPED_LIABILITY = "uncapped_liability"
    ANTI_ASSIGNMENT = "anti_assignment"
    TERMINATION_FOR_CONVENIENCE = "termination_for_convenience"
    RENEWAL_TERM = "renewal_term"
    GOVERNING_LAW = "governing_law"
    NON_COMPETE = "non_compete"
    EXCLUSIVITY = "exclusivity"
    MOST_FAVORED_NATION = "most_favored_nation"
    IP_OWNERSHIP_ASSIGNMENT = "ip_ownership_assignment"
    AUDIT_RIGHTS = "audit_rights"
    INSURANCE = "insurance"
    OTHER = "other"


class RiskLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @property
    def rank(self) -> int:
        return {"high": 3, "medium": 2, "low": 1, "none": 0}[self.value]


class FindingStatus(StrEnum):
    COMPLIANT = "compliant"
    DEVIATION = "deviation"
