from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)

from app.config import get_settings
from app.models.schemas import ReviewRequest, ReviewResult
from app.orchestrator.pipeline import review_contract
from app.pipeline.ingest import IngestionError, extract_text
from app.playbooks.loader import list_playbooks, load_playbook

router = APIRouter()

DISCLAIMER = "ClauseGuard provides review assistance, not legal advice."

# Guard against a hostile upload eating all memory before we touch it.
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


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


@router.post("/v1/reviews/file")
async def create_review_from_file(
    file: UploadFile = File(...),
    playbook_id: str = Form("vendor_saas_buyer"),
    _: str = Depends(require_api_key),
) -> dict[str, object]:
    """Review an uploaded contract (digital PDF or DOCX).

    The file is parsed to plain text by `app.pipeline.ingest`, then reviewed
    exactly as the text endpoint does — citations stay offset-valid against
    the extracted text. Scanned PDFs and unknown types are rejected.
    """
    try:
        data = await file.read()
    finally:
        await file.close()

    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit",
        )

    try:
        playbook = load_playbook(playbook_id)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    mime = (file.content_type or "").lower()
    try:
        text = extract_text(data, mime)
    except IngestionError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc

    result: ReviewResult = await review_contract(text, playbook)
    return {"disclaimer": DISCLAIMER, "result": result.model_dump()}
