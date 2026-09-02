from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.config import get_settings
from app.models.schemas import Playbook, ReviewRequest
from app.obs.logging import log
from app.orchestrator.pipeline import review_contract
from app.pipeline.ingest import IngestionError, extract_text
from app.playbooks.loader import list_playbooks, load_playbook
from app.store import STATUS_COMPLETED, STATUS_FAILED, STATUS_PENDING, ReviewStore

router = APIRouter()

# Guard against a hostile upload eating all memory before we touch it.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class RateLimiter:
    """Per-key sliding-window limiter (requests per 60s).

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


def require_api_key(x_api_key: str = Header(default="")) -> str:
    if x_api_key not in get_settings().allowed_api_keys:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
    return x_api_key


def rate_limit(x_api_key: str = Depends(require_api_key)) -> None:
    if not rate_limiter.allow(x_api_key):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Rate limit exceeded. Try again shortly.",
        )


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/playbooks", dependencies=[Depends(rate_limit)])
async def get_playbooks(_: str = Depends(require_api_key)) -> dict[str, list[str]]:
    return {"playbooks": list_playbooks()}


def _budget_day() -> str:
    return datetime.now(UTC).date().isoformat()


async def _run_review_job(store: ReviewStore, job_id: str, text: str, playbook: Playbook) -> None:
    """Run a submitted review in the background, recording each transition.

    The pipeline is plain async, so an in-process task is enough for the MVP.
    # ponytail: single-process background executor; a separate worker pool is
    # the upgrade path once jobs outlive a process restart.
    """
    await store.transition(job_id, "running")
    try:
        result = await review_contract(text, playbook)
    except Exception as exc:  # noqa: BLE001 — a failed review is a "failed job"
        try:
            await store.transition(job_id, STATUS_FAILED, error=str(exc))
        except Exception:  # store itself is down; nothing to do but log
            log.warning("job store unavailable on failure", job_id=job_id, error=str(exc))
        return
    await store.transition(job_id, STATUS_COMPLETED, result=json.dumps(result.model_dump()))
    # Charge tokens to the day they were actually consumed (a job may cross UTC
    # midnight). # ponytail: read-then-add is not atomic, so a burst racing the
    # check can overshoot by a request or two; the rate limiter keeps that small.
    spent = result.usage.input_tokens + result.usage.output_tokens
    await store.add_token_spend(_budget_day(), spent)


async def _submit_review(request: Request, playbook_id: str, text: str) -> dict[str, str]:
    try:
        playbook = load_playbook(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    store: ReviewStore = request.app.state.store
    settings = get_settings()
    if settings.max_review_chars > 0 and len(text) > settings.max_review_chars:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"Content exceeds {settings.max_review_chars} character limit",
        )
    budget_exhausted = (
        settings.daily_token_budget > 0
        and await store.tokens_spent(_budget_day()) >= settings.daily_token_budget
    )
    if budget_exhausted:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Daily token budget exhausted. Try again tomorrow.",
        )
    job_id = uuid4().hex
    await store.create(job_id, playbook_id)
    asyncio.create_task(_run_review_job(store, job_id, text, playbook))
    return {"review_id": job_id, "status": STATUS_PENDING}


@router.post(
    "/v1/reviews", dependencies=[Depends(rate_limit)], status_code=status.HTTP_202_ACCEPTED
)
async def create_review(
    req: ReviewRequest,
    request: Request,
    _: str = Depends(require_api_key),
) -> dict[str, str]:
    return await _submit_review(request, req.playbook_id, req.text)


@router.post(
    "/v1/reviews/file",
    dependencies=[Depends(rate_limit)],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_review_from_file(
    request: Request,
    file: UploadFile = File(...),
    playbook_id: str = Form("vendor_saas_buyer"),
    _: str = Depends(require_api_key),
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

    return await _submit_review(request, playbook_id, text)


@router.get("/v1/reviews/{job_id}", dependencies=[Depends(rate_limit)])
async def get_review(
    job_id: str,
    request: Request,
    _: str = Depends(require_api_key),
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
