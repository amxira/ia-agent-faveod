"""Notification settings (Slack / Teams / SMTP email)."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# --- Alert triggers ---
TENDER_ALERT_THRESHOLD = float(_env("TENDER_ALERT_THRESHOLD", "80.0"))
NOTIFY_ON_LEADS = _env("NOTIFY_ON_LEADS", "1") == "1"
LEAD_PRIORITY_FILTER = _env("LEAD_PRIORITY_FILTER", "HIGH PRIORITY")

# --- Channels (leave empty to disable a channel) ---
SLACK_WEBHOOK = _env("NOTIFY_SLACK_WEBHOOK")
TEAMS_WEBHOOK = _env("NOTIFY_TEAMS_WEBHOOK")
SMTP_HOST = _env("NOTIFY_SMTP_HOST")
SMTP_PORT = int(_env("NOTIFY_SMTP_PORT", "587"))
SMTP_USER = _env("NOTIFY_SMTP_USER")
SMTP_PASSWORD = _env("NOTIFY_SMTP_PASSWORD")
SMTP_FROM = _env("NOTIFY_SMTP_FROM")
SMTP_TO = _env("NOTIFY_SMTP_TO")

# --- Data locations (shared with the agents) ---
DATA_DIR = _env("DATA_DIR", "data")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
STATE_DIR = os.path.join(DATA_DIR, "state")

os.makedirs(STATE_DIR, exist_ok=True)
