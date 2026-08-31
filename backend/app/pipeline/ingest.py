"""File ingestion — formats in, plain text out.

One seam, `extract_text(data, mime)`, converts an uploaded contract to the same
plain text the segmenter already consumes, so citations stay offset-valid
against exactly what was reviewed. Supported: digital PDFs (embedded text
layer) and DOCX. Scanned PDFs (no text layer) and unknown types fail loudly —
never silently degraded text, which would poison the downstream citations.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

from app.obs.logging import log  # noqa: E402  (structlog bound below imports)

SUPPORTED_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class IngestionError(ValueError):
    """Raised when a file cannot be turned into trustworthy text."""


_UNSUPPORTED_MSG = (
    "Unsupported file type. Upload a digital PDF (.pdf) or Word (.docx). "
    "Scanned/image-only PDFs are not supported."
)


def extract_text(data: bytes, mime: str) -> str:
    """Convert uploaded bytes to contract text for review.

    Raises IngestionError (unhelpful for review) instead of returning garbage:
    a corrupt file or scanned PDF fails here, before any token spend.
    """
    kind = SUPPORTED_MIMES.get(mime, "")
    if kind == "pdf":
        return _extract_pdf(data)
    if kind == "docx":
        return _extract_docx(data)
    raise IngestionError(_UNSUPPORTED_MSG)


def _extract_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        pages = [(p.extract_text() or "").strip() for p in reader.pages]
    except Exception:
        # Real cause is logged, not echoed to the caller (avoid leaking parser
        # internals and confusing users with library English).
        log.exception("PDF text extraction failed")
        raise IngestionError(
            "Could not read this PDF. It may be corrupt or password-protected. "
            "Re-upload a digital PDF or Word document."
        ) from None

    text = "\n\n".join(p for p in pages if p)
    if not text:
        raise IngestionError(
            "This PDF has no extractable text layer — it is a scanned/image file. "
            "Re-upload a digital PDF or Word document."
        )
    return text


_TEXT_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _extract_docx(data: bytes) -> str:
    text = _docx_xml(data)
    root = ElementTree.fromstring(text)
    # Each `<w:p>` block is one paragraph; the segmenter splits on blank lines,
    # so emit the same "\n\n" separator the PDF path uses between pages.
    paragraphs: list[str] = []
    for para in root.iter(_TEXT_NS + "p"):
        parts: list[str] = []
        for elem in para.iter():
            if elem.tag == _TEXT_NS + "t":
                parts.append(elem.text or "")
            elif elem.tag == _TEXT_NS + "br":
                parts.append("\n")
        paragraphs.append(_tidy_docx("".join(parts)))
    return "\n\n".join(p for p in paragraphs if p)


def _docx_xml(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            return zf.read("word/document.xml").decode("utf-8")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise IngestionError(f"Not a valid Word document: {exc}") from exc


def _tidy_docx(text: str) -> str:
    # Collapse intra-paragraph whitespace so the wrapped source drives
    # paragraph breaks, then normalize any remaining hard line breaks.
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_path(path: str | Path) -> str:
    """Convenience for CLI/test use: guess the kind from the file extension."""
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = {v: k for k, v in SUPPORTED_MIMES.items()}.get(suffix)
    if mime is None:
        raise IngestionError(_UNSUPPORTED_MSG)
    return extract_text(Path(path).read_bytes(), mime)