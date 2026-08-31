from evals.risk_rules import evaluate


def test_cap_unlimited_is_deviation():
    status, risk = evaluate("Liability shall be unlimited.", "cap_on_liability")
    assert status == "deviation"
    assert risk == "high"


def test_cap_12_months_is_compliant():
    status, risk = evaluate("Liability capped at 12 months of fees.", "cap_on_liability")
    assert status == "compliant"
    assert risk == "none"


def test_cap_uncapped_is_deviation():
    status, risk = evaluate("Liability is uncapped.", "cap_on_liability")
    assert status == "deviation"
    assert risk == "high"


def test_cap_ambiguous_defaults_to_deviation():
    status, risk = evaluate("Liability shall be limited.", "cap_on_liability")
    assert status == "deviation"


def test_non_compete_any_restrict_is_deviation():
    status, risk = evaluate("Customer shall not compete.", "non_compete")
    assert status == "deviation"
    assert risk == "high"


def test_exclusivity_any_is_deviation():
    status, risk = evaluate("Customer agrees to exclusivity.", "exclusivity")
    assert status == "deviation"
    assert risk == "medium"


def test_governing_law_foreign_is_deviation():
    status, risk = evaluate("Governed by laws of Singapore.", "governing_law")
    assert status == "deviation"
    assert risk == "low"


def test_governing_law_delaware_is_compliant():
    status, risk = evaluate("Governed by laws of Delaware.", "governing_law")
    assert status == "compliant"
    assert risk == "none"


def test_anti_assignment_restrictive_is_deviation():
    status, risk = evaluate("May not assign without prior written consent.", "anti_assignment")
    assert status == "deviation"
    assert risk == "medium"


def test_anti_assignment_affiliate_ok():
    status, risk = evaluate("May assign to an affiliate or successor.", "anti_assignment")
    assert status == "compliant"
    assert risk == "none"


def test_unknown_category_returns_compliant():
    status, risk = evaluate("Some text.", "unknown_category")
    assert status == "compliant"
    assert risk == "none"
