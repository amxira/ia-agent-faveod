"""Central configuration, loaded from environment / .env."""

import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# --- Reasoning engine ---
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
# Free models on OpenRouter rotate often. The client auto-discovers a working
# free model when the configured one becomes unavailable. Paid alternative:
# deepseek/deepseek-r1 (or deepseek/deepseek-r1-0528).
LLM_MODEL = _env("LLM_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free")
LLM_BASE_URL = _env("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_TEMPERATURE = float(_env("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT = int(_env("LLM_TIMEOUT", "90"))
MAX_LLM_RETRIES = int(_env("MAX_LLM_RETRIES", "2"))

# --- Embeddings ---
GEMINI_API_KEY = _env("GEMINI_API_KEY")
EMBEDDING_PROVIDER = _env("EMBEDDING_PROVIDER", "gemini").strip().lower()
GEMINI_EMBED_MODEL = _env("GEMINI_EMBED_MODEL", "gemini-embedding-001")
GEMINI_EMBED_URL = _env(
    "GEMINI_EMBED_URL",
    "https://generativelanguage.googleapis.com/v1beta",
)
# Minimum seconds between embedding batches (free-tier RPM throttling).
GEMINI_RATE_LIMIT_SLEEP = float(_env("GEMINI_RATE_LIMIT_SLEEP", "0.5"))
VECTOR_SIZE = int(_env("VECTOR_SIZE", "768"))

# --- Vector store ---
QDRANT_URL = _env("QDRANT_URL")
QDRANT_API_KEY = _env("QDRANT_API_KEY")
QDRANT_COLLECTION = _env("QDRANT_COLLECTION", "tender_chunks")

# --- Guardrails ---
SIMILARITY_THRESHOLD = float(_env("SIMILARITY_THRESHOLD", "0.75"))
TOP_K = int(_env("TOP_K", "6"))

# --- Chunking ---
CHUNK_SIZE = int(_env("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(_env("CHUNK_OVERLAP", "120"))

# --- Scraping ---
SOURCES = [s.strip() for s in _env("SOURCES", "sample").split(",") if s.strip()]
PROXY_LIST = [p.strip() for p in _env("PROXY_LIST", "").split(",") if p.strip()]
HTTP_TIMEOUT = int(_env("HTTP_TIMEOUT", "30"))
MAX_PER_SOURCE = int(_env("MAX_PER_SOURCE", "50"))
USER_AGENT = _env(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
)

# --- Date filters (0 = disabled) ---
# Keep only tenders published (or with a deadline) within the last N days.
RECENT_DAYS = int(_env("RECENT_DAYS", "0"))

# --- Data locations ---
DATA_DIR = _env("DATA_DIR", "data")
SAMPLE_DOCS_DIR = os.path.join(DATA_DIR, "sample_docs")
DOWNLOAD_DIR = os.path.join(DATA_DIR, "downloads")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
LOG_DIR = os.path.join(DATA_DIR, "logs")

for _d in (DATA_DIR, SAMPLE_DOCS_DIR, DOWNLOAD_DIR, OUTPUT_DIR, LOG_DIR):
    os.makedirs(_d, exist_ok=True)
