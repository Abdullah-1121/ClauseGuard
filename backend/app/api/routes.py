from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from contextlib import ExitStack
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.config import Settings, get_settings
from app.models.schemas import Playbook, ReviewRequest
from app.obs.logging import log
from app.orchestrator.pipeline import review_contract
from app.pipeline import classify, evaluate
from app.pipeline.ingest import IngestionError, extract_text
from app.playbooks.loader import list_playbooks, load_playbook
from app.providers.factory import build_model
from app.store import STATUS_COMPLETED, STATUS_FAILED, STATUS_PENDING, ReviewStore

router = APIRouter()

# Guard against a hostile upload eating all memory before we touch it.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

# Bring-your-own-key providers exposed to clients. All OpenAI-compatible.
BYOK_PROVIDERS = ("groq", "openrouter")

# Model catalog served by GET /v1/models (also mirrored in the frontend).
MODEL_CATALOG: dict[str, dict[str, object]] = {
    "groq": {
        "label": "Groq",
        "base_url": "",
        "models": [
            "llama-3.3-70b-versatile",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "meta-llama/llama-3.1-8b-instant",
        ],
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            "openai/gpt-4o-mini",
            "openai/gpt-4.1-mini",
            "google/gemini-2.0-flash-001",
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat-v3-0324:free",
        ],
    },
}


class RateLimiter:
    """Per-bucket sliding-window limiter (requests per 60s).

    In-memory, no persistence — correct for a single process, which is all the
    MVP runs. # ponytail: single-process window only; move to Redis if this ever
    runs behind multiple workers.
    """

    def __init__(self, per_minute: int = 10):
        self.limit = per_minute
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        if self.limit <= 0:  # 0 = unlimited
            return True
        now = time.monotonic()
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= self.limit:
            if not hits:  # window fully drained; drop the empty key
                self._hits.pop(key, None)
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = RateLimiter(get_settings().rate_limit_per_minute)


def rate_limit_client(request: Request) -> None:
    # Bucketed by client IP, not a key: reachable endpoints carry no key and
    # BYOK reviews spend the caller's own quota, so the limiter's job is just
    # to protect the server from floods. # ponytail: IP buckets are coarse
    # behind a shared proxy; good enough for a single deployed process.
    bucket = request.client.host if request.client else "anon"
    if not rate_limiter.allow(bucket):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Rate limit exceeded. Try again shortly.",
        )


def _budget_day() -> str:
    return datetime.now(UTC).date().isoformat()


def _require_access(request: Request, byok_key: str | None) -> None:
    """BYOK bypasses the server key (the caller pays); otherwise the caller
    must present a server-issued X-API-Key."""
    if byok_key:
        return
    if request.headers.get("X-API-Key") in get_settings().allowed_api_keys:
        return
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Provide provider/api_key/model to run on your own key, "
        "or a valid X-API-Key for the server's models.",
    )


def _byok_settings(provider: str, api_key: str, model: str) -> Settings:
    """A Settings view that resolves build_model() against a caller's key."""
    settings = get_settings()
    updates: dict[str, object] = {
        "provider": provider,
        "model_cheap": model,
        "model_strong": model,
    }
    if provider == "groq":
        updates["groq_api_key"] = api_key
    elif provider == "openrouter":
        updates["openrouter_api_key"] = api_key
    return settings.model_copy(update=updates)


def _validate_byok(
    provider: str | None, api_key: str | None, model: str | None
) -> tuple[str, str, str] | None:
    """None when BYOK is absent; raises 400 on a half-filled or unknown combo."""
    if provider is None and api_key is None and model is None:
        return None
    if provider not in BYOK_PROVIDERS or not api_key or not model:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Set provider (one of {', '.join(BYOK_PROVIDERS)}), api_key, and model together",
        )
    return provider, api_key, model


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/models", dependencies=[Depends(rate_limit_client)])
async def get_models() -> dict[str, object]:
    return {"providers": MODEL_CATALOG}


@router.get("/v1/playbooks", dependencies=[Depends(rate_limit_client)])
async def get_playbooks() -> dict[str, list[str]]:
    return {"playbooks": list_playbooks()}


async def _run_review_job(
    store: ReviewStore,
    job_id: str,
    text: str,
    playbook: Playbook,
    byok: tuple[str, str, str] | None = None,
) -> None:
    """Run a submitted review in the background, recording each transition.

    With BYOK set, the classifier/evaluator agents are swapped to the caller's
    models for the duration of the run — the same Agent.override() mechanism the
    test suite uses, so retries/batching/guardrails are untouched.
    # ponytail: single-process background executor; a separate worker pool is
    # the upgrade path once jobs outlive a process restart.
    """
    await store.transition(job_id, "running")
    try:
        if byok is None:
            result = await review_contract(text, playbook)
        else:
            provider, api_key, model = byok
            settings = _byok_settings(provider, api_key, model)
            cheap = build_model("cheap", settings)
            strong = build_model("strong", settings)
            with ExitStack() as stack:
                stack.enter_context(classify.classifier_agent.override(model=cheap))
                stack.enter_context(classify.batch_classifier_agent.override(model=cheap))
                stack.enter_context(evaluate.evaluator_agent.override(model=strong))
                result = await review_contract(text, playbook)
    except Exception as exc:  # noqa: BLE001 — a failed review is a "failed job"
        try:
            await store.transition(job_id, STATUS_FAILED, error=str(exc))
        except Exception:  # store itself is down; nothing to do but log
            log.warning("job store unavailable on failure", job_id=job_id, error=str(exc))
        return
    await store.transition(job_id, STATUS_COMPLETED, result=json.dumps(result.model_dump()))
    # Charge server-funded runs to the day they were consumed (BYOK spends the
    # caller's quota, not ours). # ponytail: read-then-add is not atomic, so a
    # burst racing the check can overshoot by a request or two; the rate
    # limiter keeps that small.
    if byok is None:
        spent = result.usage.input_tokens + result.usage.output_tokens
        await store.add_token_spend(_budget_day(), spent)


async def _submit_review(
    request: Request,
    playbook_id: str,
    text: str,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, str]:
    byok = _validate_byok(provider, api_key, model)
    _require_access(request, byok[1] if byok else None)
    store: ReviewStore = request.app.state.store
    settings = get_settings()
    if settings.max_review_chars > 0 and len(text) > settings.max_review_chars:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Content exceeds {settings.max_review_chars} character limit",
        )
    budget_exhausted = (
        byok is None
        and settings.daily_token_budget > 0
        and await store.tokens_spent(_budget_day()) >= settings.daily_token_budget
    )
    if budget_exhausted:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Daily token budget exhausted. Try again tomorrow.",
        )
    try:
        playbook = load_playbook(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    job_id = uuid4().hex
    await store.create(job_id, playbook_id)
    asyncio.create_task(_run_review_job(store, job_id, text, playbook, byok=byok))
    return {"review_id": job_id, "status": STATUS_PENDING}


@router.post(
    "/v1/reviews",
    dependencies=[Depends(rate_limit_client)],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_review(
    req: ReviewRequest,
    request: Request,
) -> dict[str, str]:
    return await _submit_review(
        request, req.playbook_id, req.text, req.provider, req.api_key, req.model
    )


@router.post(
    "/v1/reviews/file",
    dependencies=[Depends(rate_limit_client)],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_review_from_file(
    request: Request,
    file: UploadFile = File(...),
    playbook_id: str = Form("vendor_saas_buyer"),
    provider: str = Form(""),
    api_key: str = Form(""),
    model: str = Form(""),
) -> dict[str, str]:
    """Submit a contract (digital PDF or DOCX) for review.

    The file is parsed to plain text, then queued exactly as the text endpoint
    does — citations stay offset-valid against the extracted text. Scanned PDFs
    and unknown types are rejected before a job is created.
    """
    try:
        data = await file.read()
    finally:
        await file.close()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
        )

    mime = (file.content_type or "").lower()
    try:
        text = extract_text(data, mime)
    except IngestionError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    return await _submit_review(
        request,
        playbook_id,
        text,
        provider or None,
        api_key or None,
        model or None,
    )


@router.get("/v1/reviews/{job_id}", dependencies=[Depends(rate_limit_client)])
async def get_review(
    job_id: str,
    request: Request,
) -> dict[str, object]:
    row = await request.app.state.store.get(job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Review not found")

    payload: dict[str, object] = {"review_id": row["id"], "status": row["status"]}
    if row["result"] is not None:
        payload["result"] = json.loads(row["result"])
    if row["error"] is not None:
        payload["error"] = row["error"]
    return payload
