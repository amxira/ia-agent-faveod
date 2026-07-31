"""Saved-items store (Task 6.1): bookmark tenders / partners / leads.

Kept as a simple JSON file so the dashboard and the chat agent share the same
source of truth without needing a database.
"""

from __future__ import annotations

import json
import logging
import os

from tender_hunter import config

log = logging.getLogger(__name__)

SAVED_FILE = os.path.join(config.DATA_DIR, "saved.json")

KINDS = ("tenders", "partners", "leads")


def _blank() -> dict:
    return {kind: [] for kind in KINDS}


def load_saved() -> dict:
    """Return {kind: [item_id, ...]} for all saved kinds."""
    if not os.path.exists(SAVED_FILE):
        return _blank()
    try:
        with open(SAVED_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return _blank()
        return {kind: list(data.get(kind) or []) for kind in KINDS}
    except Exception as exc:  # noqa: BLE001 - a broken store must not crash the UI
        log.warning("could not read %s: %s", SAVED_FILE, exc)
        return _blank()


def _write(data: dict) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(SAVED_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def is_saved(kind: str, item_id: str) -> bool:
    if kind not in KINDS:
        return False
    return item_id in load_saved().get(kind, [])


def save_item(kind: str, item_id: str) -> dict:
    """Bookmark an item. Returns the action taken."""
    if kind not in KINDS:
        return {"ok": False, "reason": f"unknown kind {kind!r}"}
    data = load_saved()
    items = data[kind]
    if item_id in items:
        return {"ok": True, "kind": kind, "item_id": item_id, "already_saved": True}
    items.append(item_id)
    _write(data)
    return {"ok": True, "kind": kind, "item_id": item_id, "already_saved": False}


def remove_item(kind: str, item_id: str) -> dict:
    if kind not in KINDS:
        return {"ok": False, "reason": f"unknown kind {kind!r}"}
    data = load_saved()
    items = data[kind]
    if item_id not in items:
        return {"ok": True, "kind": kind, "item_id": item_id, "was_saved": False}
    data[kind] = [i for i in items if i != item_id]
    _write(data)
    return {"ok": True, "kind": kind, "item_id": item_id, "was_saved": True}


def list_saved(kind: str) -> list[str]:
    if kind not in KINDS:
        return []
    return load_saved().get(kind, [])


def all_saved() -> dict:
    return load_saved()
