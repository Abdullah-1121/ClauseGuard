"""HTTP endpoint tests — drive the real ASGI app through httpx.

The app runs in-loop via ASGITransport, so pydantic-ai's contextvar-based
agent overrides (TestModel) reach the pipeline. The sync TestClient runs the
app in a separate thread where contextvars do not propagate, so it is not
used here.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import httpx
import pytest
from pydantic_ai.models.test import TestModel

from app.api.routes import rate_limiter
from app.config import get_settings
from app.main import app
from app.models.schemas import ReviewResult, UsageStats
from app.pipeline import classify, evaluate
from app.store import ReviewStore
from tests.test_ingest import DOCX_MIME, build_docx

AUTH = {"X-API-Key": "dev-local-key"}
CONTRACT = (
    "1. Limitation of Liability. Vendor's liability shall be unlimited.\n\n"
    "2. Term. This Agreement automatically renews each year."
)


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Pin the accepted key deterministically, whatever the local .env holds.
    known = get_settings().model_copy(update={"api_keys": AUTH["X-API-Key"]})
    monkeypatch.setattr("app.api.routes.get_settings", lambda: known)
    # ASGITransport does not run the app lifespan; give each test a fresh store.
    app.state.store = ReviewStore(str(tmp_path / "jobs.db"))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _wait_completed(client, review_id, status="completed") -> dict:
    for _ in range(100):
        res = await client.get(f"/v1/reviews/{review_id}", headers=AUTH)
        assert res.status_code == 200
        body = res.json()
        if body["status"] == status:
            return body
        await asyncio.sleep(0.01)
    raise AssertionError(f"review did not reach {status!r} in time: {body!r}")


@pytest.fixture(autouse=True)
def _clean_limiter():
    # The limiter is a module singleton shared across tests; give each test a
    # clean window so counts never leak between cases.
    rate_limiter.reset()
    yield


@pytest.fixture
def offline_models():
    with (
        classify.classifier_agent.override(model=TestModel()),
        evaluate.evaluator_agent.override(model=TestModel()),
    ):
        yield


async def test_healthz_is_open(client):
    res = await client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


async def test_playbooks_open(client):
    res = await client.get("/v1/playbooks")
    assert res.status_code == 200
    assert "vendor_saas_buyer" in res.json()["playbooks"]


async def test_models_open(client):
    res = await client.get("/v1/models")
    assert res.status_code == 200
    providers = res.json()["providers"]
    assert set(providers) == {"groq", "openrouter"}
    assert "llama-3.3-70b-versatile" in providers["groq"]["models"]


async def test_review_requires_key(client):
    res = await client.post("/v1/reviews", json={"text": CONTRACT})
    assert res.status_code == 401


def _fake_result() -> ReviewResult:
    return ReviewResult(
        playbook_id="vendor_saas_buyer",
        clause_count=0,
        findings=[],
        usage=UsageStats(),
    )


async def test_review_byok_without_server_key(client, monkeypatch):
    async def fake_review(_text, _playbook, **_):  # noqa: ANN001
        return _fake_result()

    monkeypatch.setattr("app.api.routes.review_contract", fake_review)
    res = await client.post(
        "/v1/reviews",
        json={
            "text": CONTRACT,
            "provider": "groq",
            "api_key": "user-key",
            "model": "llama-3.3-70b-versatile",
        },
    )
    assert res.status_code == 202
    body = await _wait_completed(client, res.json()["review_id"])
    assert body["status"] == "completed"
    # BYOK runs on the caller's quota and must never hit the server budget.
    today = datetime.now(UTC).date().isoformat()
    assert await app.state.store.tokens_spent(today) == 0


async def test_review_byok_bypasses_exhausted_server_budget(client, monkeypatch):
    capped = get_settings().model_copy(update={"daily_token_budget": 50, "max_review_chars": 0})
    monkeypatch.setattr("app.api.routes.get_settings", lambda: capped)
    today = datetime.now(UTC).date().isoformat()
    await app.state.store.add_token_spend(today, 50)

    async def fake_review(_text, _playbook, **_):  # noqa: ANN001
        return _fake_result()

    monkeypatch.setattr("app.api.routes.review_contract", fake_review)
    res = await client.post(
        "/v1/reviews",
        json={
            "text": CONTRACT,
            "provider": "openrouter",
            "api_key": "user-key",
            "model": "openai/gpt-4o-mini",
        },
    )
    assert res.status_code == 202


async def test_review_byok_half_filled_rejected(client):
    res = await client.post(
        "/v1/reviews",
        json={"text": CONTRACT, "provider": "groq", "api_key": "user-key"},
    )
    assert res.status_code == 400


async def test_review_unknown_playbook(client, offline_models):
    res = await client.post(
        "/v1/reviews", json={"text": CONTRACT, "playbook_id": "nope"}, headers=AUTH
    )
    assert res.status_code == 404


async def test_review_returns_grounded_findings(client, offline_models):
    res = await client.post("/v1/reviews", json={"text": CONTRACT}, headers=AUTH)
    assert res.status_code == 202
    job = res.json()
    assert job["status"] == "pending"
    body = await _wait_completed(client, job["review_id"])
    result = body["result"]
    assert result["clause_count"] == 2
    findings = result["findings"]
    assert len(findings) == 2
    for finding in findings:
        citation = finding["citation"]
        assert CONTRACT[citation["start"] : citation["end"]] == citation["text"]
    # A finished review must be charged to today's token budget.
    today = datetime.now(UTC).date().isoformat()
    assert await app.state.store.tokens_spent(today) > 0


async def test_review_failure_marks_job_failed(client, offline_models, monkeypatch):
    async def boom(_text, _playbook, **_):  # noqa: ANN001
        raise RuntimeError("model blew up")

    monkeypatch.setattr("app.api.routes.review_contract", boom)
    res = await client.post("/v1/reviews", json={"text": CONTRACT}, headers=AUTH)
    assert res.status_code == 202
    body = await _wait_completed(client, res.json()["review_id"], status="failed")
    assert "model blew up" in body["error"]
    assert "result" not in body


async def test_get_review_missing(client):
    res = await client.get("/v1/reviews/does-not-exist", headers=AUTH)
    assert res.status_code == 404


async def test_review_file_requires_key(client):
    res = await client.post("/v1/reviews/file", files={"file": ("x.docx", build_docx(), DOCX_MIME)})
    assert res.status_code == 401


async def test_review_file_unsupported_type(client, offline_models):
    res = await client.post(
        "/v1/reviews/file",
        files={"file": ("x.txt", b"hello", "text/plain")},
        headers=AUTH,
    )
    assert res.status_code == 415


async def test_review_file_bad_zip(client, offline_models):
    res = await client.post(
        "/v1/reviews/file",
        files={"file": ("x.docx", b"not a zip", DOCX_MIME)},
        headers=AUTH,
    )
    assert res.status_code == 415


async def test_review_file_too_large(client, offline_models):
    big = b"0" * (10 * 1024 * 1024 + 1)
    res = await client.post(
        "/v1/reviews/file",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=AUTH,
    )
    assert res.status_code == 413


async def test_review_file_docx_ok(client, offline_models):
    res = await client.post(
        "/v1/reviews/file",
        files={"file": ("contract.docx", build_docx(), DOCX_MIME)},
        headers=AUTH,
    )
    assert res.status_code == 202
    body = await _wait_completed(client, res.json()["review_id"])
    result = body["result"]
    assert result["clause_count"] == 2
    assert result["findings"]


async def test_rate_limit_blocks_over_limit(client, monkeypatch, offline_models):
    # Shrink the window so the test doesn't wait; 4th call in the same second
    # as 3 allowed ones must be rejected, and healthz stays open for probes.
    monkeypatch.setattr("app.api.routes.rate_limiter.limit", 3)
    for _ in range(3):
        assert (await client.get("/v1/playbooks", headers=AUTH)).status_code == 200
    assert (await client.get("/v1/playbooks", headers=AUTH)).status_code == 429
    assert (await client.get("/healthz")).status_code == 200


async def test_review_blocked_by_char_cap(client, monkeypatch, offline_models):
    small = get_settings().model_copy(update={"max_review_chars": 10})
    monkeypatch.setattr("app.api.routes.get_settings", lambda: small)
    res = await client.post("/v1/reviews", json={"text": CONTRACT}, headers=AUTH)
    assert res.status_code == 413
    assert "character limit" in res.json()["detail"]


async def test_review_blocked_when_daily_budget_spent(client, monkeypatch, offline_models):
    capped = get_settings().model_copy(update={"daily_token_budget": 50, "max_review_chars": 0})
    monkeypatch.setattr("app.api.routes.get_settings", lambda: capped)
    today = datetime.now(UTC).date().isoformat()
    await app.state.store.add_token_spend(today, 50)
    res = await client.post("/v1/reviews", json={"text": CONTRACT}, headers=AUTH)
    assert res.status_code == 429
    assert "budget" in res.json()["detail"]
