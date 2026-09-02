import zipfile
from io import BytesIO

import pytest

from app.pipeline.ingest import (
    IngestionError,
    _extract_pdf,
    extract_text,
    extract_text_from_path,
)

MINIMAL_DOCX = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Limitation of Liability.</w:t></w:r>
      <w:r><w:t> Vendor liability shall be unlimited.</w:t></w:r></w:p>
    <w:p><w:r><w:t>Governing law is Delaware.</w:t></w:r></w:p>
  </w:body>
</w:document>
"""

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def build_docx() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType='
            '"application/vnd.openxmlformats-officedocument.wordprocessingml.'
            'document.main+xml"/>'
            "</Types>",
        )
        zf.writestr("word/document.xml", MINIMAL_DOCX)
    return buf.getvalue()


def test_docx_round_trip_extracts_paragraph_text():
    text = extract_text(build_docx(), DOCX_MIME)
    assert "Limitation of Liability. Vendor liability shall be unlimited." in text
    assert "Governing law is Delaware." in text


def test_docx_bad_zip_raises():
    with pytest.raises(IngestionError):
        extract_text(b"not a zip at all", DOCX_MIME)


def test_unknown_mime_raises():
    with pytest.raises(IngestionError, match="Unsupported"):
        extract_text(b"hello", "text/plain")


def test_pdf_with_no_text_layer_raises(monkeypatch):
    from pypdf import PdfWriter

    # A real blank PDF has no extractable text — the honest scanned-file case.
    blank = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(blank)

    with pytest.raises(IngestionError, match="scanned"):
        _extract_pdf(blank.getvalue())


def test_pdf_extracts_page_text(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "Section 3.2 Assignment without consent."

    class FakeReader:
        def __init__(self, _data):  # noqa: N803
            self.pages = [FakePage(), FakePage()]

    monkeypatch.setattr("app.pipeline.ingest.PdfReader", FakeReader)
    text = _extract_pdf(b"fake pdf bytes")
    assert "Assignment without consent." in text
    assert "\n\n" in text  # pages joined with the segmenter's separator


def test_invalid_pdf_bytes_raise_ingestion_error(monkeypatch):
    def boom(_data):  # noqa: N803
        raise RuntimeError("corrupt stream")

    monkeypatch.setattr("app.pipeline.ingest.PdfReader", boom)
    with pytest.raises(IngestionError, match="Could not read this PDF"):
        _extract_pdf(b"garbage")


def test_extract_text_from_path_dispatches_by_ext(tmp_path, monkeypatch):
    p = tmp_path / "contract.docx"
    p.write_bytes(build_docx())
    assert "Delaware" in extract_text_from_path(p)

    p2 = tmp_path / "contract.txt"
    p2.write_bytes(b"nope")
    with pytest.raises(IngestionError, match="Unsupported"):
        extract_text_from_path(p2)
