from app.models.schemas import Citation
from app.pipeline.guardrails import needs_human_review, verify_citation

SOURCE = "The liability cap is twelve months of fees."


def test_valid_citation_passes():
    cit = Citation(start=4, end=18, text=SOURCE[4:18])
    assert verify_citation(SOURCE, cit) is True


def test_hallucinated_citation_rejected():
    cit = Citation(start=4, end=18, text="something else entirely")
    assert verify_citation(SOURCE, cit) is False


def test_out_of_bounds_citation_rejected():
    cit = Citation(start=0, end=999, text=SOURCE)
    assert verify_citation(SOURCE, cit) is False


def test_confidence_gate():
    assert needs_human_review(0.4, 0.55) is True
    assert needs_human_review(0.9, 0.55) is False
