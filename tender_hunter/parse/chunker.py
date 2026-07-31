"""Page-aware text chunker.

Chunks are cut on paragraph boundaries with overlap so context around a clause
is preserved for retrieval. Each chunk remembers the page it starts on, which
feeds the citation layer.
"""

from __future__ import annotations

import re

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    page: int


def _paragraphs(text: str) -> list[tuple[str, int]]:
    """Split text into (paragraph, starting_char_offset) pairs."""
    out: list[tuple[str, int]] = []
    offset = 0
    for raw in re.split(r"\n\s*\n", text):
        para = re.sub(r"[ \t]+", " ", raw).strip()
        if para:
            out.append((para, offset))
        offset += len(raw) + 2
    return out


def _page_of(offset: int, page_offsets: list[int]) -> int:
    for idx, start in enumerate(page_offsets):
        if offset < start:
            return max(idx, 1)
    return max(len(page_offsets), 1)


def chunk_text(pages: list[str], chunk_size: int = 900, overlap: int = 120) -> list[Chunk]:
    """Chunk page texts while tracking the source page of each chunk."""
    if not pages:
        return []

    page_offsets: list[int] = []
    total = 0
    for page in pages:
        page_offsets.append(total)
        total += len(page) + 2
    full = "\n\n".join(pages)

    paras = _paragraphs(full)
    if not paras:
        return []

    chunks: list[Chunk] = []
    buf = ""
    buf_start = 0
    for para, offset in paras:
        if len(para) > chunk_size:
            if buf.strip():
                chunks.append(Chunk(text=buf.strip(), page=_page_of(buf_start, page_offsets)))
            buf, buf_start = "", 0
            for i in range(0, len(para), chunk_size - overlap):
                chunks.append(Chunk(text=para[i : i + chunk_size].strip(), page=_page_of(offset + i, page_offsets)))
            continue

        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) > chunk_size and buf:
            chunks.append(Chunk(text=buf.strip(), page=_page_of(buf_start, page_offsets)))
            tail = buf[-overlap:]
            buf = f"{tail} {para}" if tail.strip() else para
            buf_start = max(offset - overlap, 0)
        else:
            if not buf:
                buf_start = offset
            buf = candidate

    if buf.strip():
        chunks.append(Chunk(text=buf.strip(), page=_page_of(buf_start, page_offsets)))

    return chunks
