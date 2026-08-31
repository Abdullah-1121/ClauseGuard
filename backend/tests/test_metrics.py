from evals.metrics import aggregate, counts_for, llm_agreement, risk_accuracy


def test_counts_for():
    c = counts_for({"a", "b"}, {"b", "c"})
    assert (c.tp, c.fp, c.fn) == (1, 1, 1)


def test_perfect_score():
    m = aggregate([({"a", "b"}, {"a", "b"})])
    assert m["precision"] == 1.0
    assert m["recall"] == 1.0
    assert m["f1"] == 1.0


def test_mixed_score():
    m = aggregate([({"a"}, {"a", "b"}), ({"x"}, {"x"})])
    # tp=2, fp=0, fn=1 -> precision 1.0, recall 0.667
    assert m["precision"] == 1.0
    assert m["recall"] == round(2 / 3, 4)


def test_risk_accuracy_perfect():
    r = risk_accuracy([("high", "high"), ("low", "low")])
    assert r["risk_accuracy"] == 1.0
    assert r["correct"] == 2
    assert r["total"] == 2


def test_risk_accuracy_mixed():
    r = risk_accuracy([("high", "high"), ("high", "low"), ("medium", "medium")])
    assert r["risk_accuracy"] == round(2 / 3, 4)


def test_risk_accuracy_empty():
    r = risk_accuracy([])
    assert r["risk_accuracy"] == 0.0
    assert r["total"] == 0


def test_llm_agreement_perfect():
    a = llm_agreement([("deviation", "deviation"), ("compliant", "compliant")])
    assert a["llm_agreement"] == 1.0


def test_llm_agreement_mixed():
    a = llm_agreement([("deviation", "deviation"), ("compliant", "deviation")])
    assert a["llm_agreement"] == 0.5
