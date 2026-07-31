"""Agent-3 configuration. Reuses shared infra settings from Agent 1, adds
event-mapper-specific ones. All values come from environment / .env."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from tender_hunter.config import (  # shared infra settings (LLM, proxy, timeout)
    HTTP_TIMEOUT,
    LLM_MODEL,
    LLM_TIMEOUT,
    MAX_LLM_RETRIES,
    OPENROUTER_API_KEY,
    PROXY_LIST,
    USER_AGENT,
)

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# --- Event collection (Task 4.1) ---
# Backend: "sample" (offline demo) | "ten_times" | "eventbrite" | "luma" | "news"
EVENT_SOURCE = _env("EVENT_SOURCE", "sample").strip().lower()
EVENT_COUNTRIES = [
    c.strip()
    for c in _env(
        "EVENT_COUNTRIES",
        "Morocco,Senegal,Tunisia,Egypt,Saudi Arabia,United Arab Emirates",
    ).split(",")
    if c.strip()
]
EVENT_KEYWORDS = [
    k.strip()
    for k in _env(
        "EVENT_KEYWORDS",
        "IT Summit,Digital Transformation Africa,Cybersecurity Conference,CIO Summit,Technology Summit",
    ).split(",")
    if k.strip()
]
MAX_EVENTS = int(_env("MAX_EVENTS", "20"))
EVENT_FETCH_TIMEOUT = int(_env("EVENT_FETCH_TIMEOUT", "45"))

# --- Page scraping & NER (Task 4.2) ---
MAX_PAGES_PER_EVENT = int(_env("MAX_PAGES_PER_EVENT", "6"))
MIN_PAGE_TEXT_CHARS = int(_env("MIN_PAGE_TEXT_CHARS", "200"))
MAX_PAGE_TEXT_CHARS = int(_env("MAX_PAGE_TEXT_CHARS", "9000"))

# --- Lead scoring (Task 4.3) ---
MAX_LEADS = int(_env("MAX_LEADS", "40"))
PRIORITY_THRESHOLD = float(_env("PRIORITY_THRESHOLD", "70.0"))

# --- Data locations ---
DATA_DIR = _env("DATA_DIR", "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
LOG_DIR = os.path.join(DATA_DIR, "logs")

for _d in (OUTPUT_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)
