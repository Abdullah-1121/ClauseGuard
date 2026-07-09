"""HTTP API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import get_settings
from app.models.schemas import ReviewRequest, ReviewResult
from app.orchestrator.pipeline import review_contract
from app.playbooks.loader import list_playbooks, load_playbook

router = APIRouter()

DISCLAIMER = "ClauseGuard provides review assistance, not legal advice."


def require_api_key(x_api_key: str = Header(default="")) -> str:
    if x_api_key not in get_settings().allowed_api_keys:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or missing API key")
    return x_api_key


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/playbooks")
async def get_playbooks(_: str = Depends(require_api_key)) -> dict[str, list[str]]:
    return {"playbooks": list_playbooks()}


@router.post("/v1/reviews")
async def create_review(
    req: ReviewRequest, _: str = Depends(require_api_key)
) -> dict[str, object]:
    try:
        playbook = load_playbook(req.playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    result: ReviewResult = await review_contract(req.text, playbook)
    return {"disclaimer": DISCLAIMER, "result": result.model_dump()}
