from evals.metrics import aggregate, counts_for


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
