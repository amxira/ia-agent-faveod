"""Dashboard data loader (Task 5.1). Reads the agents' latest output files.

Kept Streamlit-free so it can be unit-tested without a browser.
"""

from __future__ import annotations

import json
import os

from notifications import config

OUTPUT_DIR = config.OUTPUT_DIR


def read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - a broken file must not crash the dashboard
        return {}


def _entries(name: str, key: str, fallback: str = "") -> list[dict]:
    payload = read_json(os.path.join(OUTPUT_DIR, name))
    items = payload.get(key)
    if not items and fallback:
        items = payload.get(fallback)
    return list(items or [])


def load_tenders() -> list[dict]:
    return _entries("latest.json", "reports")


def load_partners() -> list[dict]:
    return _entries("partners_latest.json", "partners")


def load_qualified_partners() -> list[dict]:
    return _entries("qualified_partners.json", "qualified_partners", "partners")


def load_events() -> list[dict]:
    return _entries("events_latest.json", "events")


def load_leads() -> list[dict]:
    return _entries("leads_latest.json", "leads")


def load_priority_leads() -> list[dict]:
    return _entries("priority_leads.json", "priority_leads", "leads")


def summary() -> dict:
    tenders = load_tenders()
    partners = load_partners()
    qualified = load_qualified_partners()
    events = load_events()
    leads = load_leads()
    return {
        "tenders": len(tenders),
        "high_value_tenders": len([t for t in tenders if (t.get("fit_score") or 0) >= 80]),
        "avg_tender_score": round(sum(float(t.get("fit_score") or 0) for t in tenders) / len(tenders), 1) if tenders else 0.0,
        "partners": len(partners),
        "qualified_partners": len([p for p in partners if p.get("qualified")]),
        "events": len(events),
        "leads": len(leads),
        "priority_leads": len([l for l in leads if l.get("priority") == "HIGH PRIORITY"]),
    }
