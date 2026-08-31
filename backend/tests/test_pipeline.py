from pydantic_ai.exceptions import ModelHTTPError
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


def test_retryable_errors_only_include_rate_limits_and_parse_failures():
    def err(status: int, body=None) -> ModelHTTPError:
        return ModelHTTPError(status, "test-model", body)

    assert classify.is_retryable_model_error(err(413, {"error": {"code": "rate_limit_exceeded"}}))
    assert classify.is_retryable_model_error(err(429))
    assert classify.is_retryable_model_error(
        err(400, {"error": {"code": "output_parse_failed"}})
    )
    assert not classify.is_retryable_model_error(err(400, {"error": {"code": "invalid_request"}}))
    assert not classify.is_retryable_model_error(
        err(404, {"error": {"code": "model_not_found"}})
    )
    assert not classify.is_retryable_model_error(err(500))
