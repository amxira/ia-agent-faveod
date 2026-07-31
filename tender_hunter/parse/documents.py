"""Document parsing (Task 2.2).

PyMuPDF is used for PDFs, python-docx for DOCX, and a lightweight HTML/txt
fallback covers the rest. `extract_pages` returns one text block per page so
citations can point to a precise page number.
"""

from __future__ import annotations

import logging
import os
import re

log = logging.getLogger(__name__)


def _read_bytes(path: str) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()


def _pdf_pages(data: bytes) -> list[str]:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        pages = []
        for page in doc:
            pages.append(page.get_text("text") or "")
        return pages
    finally:
        doc.close()


def _docx_pages(data: bytes) -> list[str]:
    from docx import Document
    from io import BytesIO

    doc = Document(BytesIO(data))
    text = "\n".join(p.text for p in doc.paragraphs)
    return [text]


def _plain_pages(data: bytes) -> list[str]:
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", text)  # strip html tags
    text = re.sub(r"\s+", " ", text)
    return [text]


def extract_pages(path: str) -> list[str]:
    """Extract per-page text from a supported document. Returns [""] on failure."""
    if not os.path.exists(path):
        log.warning("document not found: %s", path)
        return [""]
    ext = os.path.splitext(path)[1].lower()
    try:
        data = _read_bytes(path)
        if ext == ".pdf":
            return _pdf_pages(data)
        if ext == ".docx":
            return _docx_pages(data)
        return _plain_pages(data)
    except Exception as exc:  # noqa: BLE001 - parsing must never kill the pipeline
        log.warning("failed to parse %s: %s", path, exc)
        return [""]


def extract_text(path: str) -> str:
    return "\n\n".join(p for p in extract_pages(path) if p.strip())
