"""Agent-2 configuration. Reuses shared infra settings from Agent 1, adds
partner-scout-specific ones. All values come from environment / .env."""

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


# --- Search (Task 3.1) ---
# Backend: "sample" (offline demo, zero network) | "searxng" (self-hosted meta-search).
SEARCH_SOURCE = _env("SEARCH_SOURCE", "sample").strip().lower()
SEARXNG_URL = _env("SEARXNG_URL", "http://localhost:8080")
SEARXNG_TIMEOUT = int(_env("SEARXNG_TIMEOUT", "45"))
SEARCH_TERMS = [
    t.strip()
    for t in _env(
        "SEARCH_TERMS",
        "Software Engineering,Systems Integrator,IT Services,Custom Software Development",
    ).split(",")
    if t.strip()
]
TARGET_COUNTRIES = [
    c.strip()
    for c in _env(
        "TARGET_COUNTRIES",
        "Morocco,Senegal,Tunisia,Egypt,Saudi Arabia,United Arab Emirates",
    ).split(",")
    if c.strip()
]
SEARCH_PER_QUERY = int(_env("SEARCH_PER_QUERY", "10"))
MAX_COMPANIES = int(_env("MAX_COMPANIES", "40"))

# --- Website & portfolio analysis (Task 3.2) ---
MAX_PAGES_PER_COMPANY = int(_env("MAX_PAGES_PER_COMPANY", "8"))
MIN_PAGE_TEXT_CHARS = int(_env("MIN_PAGE_TEXT_CHARS", "200"))
MAX_PAGE_TEXT_CHARS = int(_env("MAX_PAGE_TEXT_CHARS", "9000"))

# --- Qualification (Task 3.3) ---
AFFINITY_THRESHOLD = float(_env("AFFINITY_THRESHOLD", "60.0"))

# --- Data locations ---
DATA_DIR = _env("DATA_DIR", "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
LOG_DIR = os.path.join(DATA_DIR, "logs")

for _d in (OUTPUT_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)
