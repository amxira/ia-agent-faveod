"""HTML extraction helpers for the event-page scraper (Task 4.2)."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

_BLOCKLIST = {"script", "style", "noscript", "iframe", "svg", "head", "template"}
_BOILERPLATE = ("nav", "footer", "form", "dialog")

_WS = re.compile(r"\s+")


def html_to_text(html: str, max_chars: int = 9000) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_BLOCKLIST):
        tag.decompose()
    for tag in soup.find_all(_BOILERPLATE):
        tag.decompose()

    parts: list[str] = []
    for node in soup.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "blockquote", "figcaption"]):
        text = _WS.sub(" ", node.get_text(" ", strip=True)).strip()
        if text:
            parts.append(text)
    if not parts:
        body = soup.get_text(" ", strip=True)
        if body:
            parts.append(_WS.sub(" ", body).strip())

    return "\n".join(parts)[:max_chars].strip()


def html_title(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    return _WS.sub(" ", title).strip()[:200]


_PAGE_KINDS = (
    (("speaker", "speakers", "faculty", "panelist"), "speakers"),
    (("agenda", "schedule", "program", "programme", "sessions"), "agenda"),
    (("attendee", "attendees", "delegate", "delegates", "participant"), "attendees"),
    (("about", "overview"), "about"),
)

_IGNORE_PATHS = ("/wp-content", "/wp-includes", "/uploads", "/assets", "/static", "/js", "/css", "/images", "/login", "/register", "/tickets")


def classify_page(url: str, anchor_text: str = "") -> str:
    path = urlparse(url).path.lower().strip("/")
    if not path:
        return "home"
    blob = f"{path} {anchor_text.lower()}"
    for tokens, kind in _PAGE_KINDS:
        if any(tok in blob for tok in tokens):
            return kind
    return "unknown"


def is_fetchable(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    lower = parsed.path.lower()
    if lower.endswith((".pdf", ".doc", ".docx", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".mp4")):
        return False
    if any(ignored in lower for ignored in _IGNORE_PATHS):
        return False
    return True
