from pydantic_ai.models.test import TestModel

from app.orchestrator.pipeline import review_contract
from app.pipeline import classify, evaluate
from app.playbooks.loader import load_playbook

CONTRACT = (
    "1. Limitation of Liability. Vendor's liability shall be unlimited.\n\n"
    "2. Term. This Agreement automatically renews each year."
)


async def test_review_runs_end_to_end_without_network():
    playbook = load_playbook("vendor_saas_buyer")
    # Override both agents with a deterministic, offline test model.
    with (
        classify.classifier_agent.override(model=TestModel()),
        evaluate.evaluator_agent.override(model=TestModel()),
    ):
        result = await review_contract(CONTRACT, playbook)

    assert result.clause_count == 2
    # Every emitted finding must carry a grounded, verifiable citation.
    for finding in result.findings:
        assert CONTRACT[finding.citation.start : finding.citation.end] == finding.citation.text
