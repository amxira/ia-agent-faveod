"""Control-layer tests (pytest-free).

Run:  python tests/test_control.py
Covers: date filters in the tender/event registries, and the saved-items store.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tender_hunter.ingest import registry as tender_registry
from event_mapper.ingest import registry as event_registry
from tender_hunter.models import Tender
from event_mapper.models import ITEvent

from control import saved as saved_store


def _tender(publication: str | None, deadline: str | None) -> Tender:
    return Tender(id=publication or "x", source="sample", title="t", publication_date=publication, deadline=deadline)


def test_tender_recent_filter():
    t5 = _tender("2026-07-25", None)
    t40 = _tender("2026-06-20", None)
    t_none = _tender(None, None)
    kept = tender_registry._recent([t5, t40, t_none], days=10)
    assert kept == [t5], f"expected only the 5-day-old tender, got {kept}"
    assert tender_registry._recent([t5, t40], days=0) == [t5, t40], "days=0 must disable the filter"
    assert tender_registry._recent([t5, t40], days=365) == [t5, t40], "wide window keeps everything dated"
    print("ok test_tender_recent_filter")


def test_tender_fetch_applies_filter():
    old = tender_registry.config.RECENT_DAYS
    try:
        tender_registry.config.RECENT_DAYS = 10
        kept = tender_registry.fetch_all(["sample"])
        assert all(t.publication_date for t in kept), "filter must drop undated tenders"
    finally:
        tender_registry.config.RECENT_DAYS = old
    print(f"ok test_tender_fetch_applies_filter ({len(kept)} recent sample tenders)")


def _event(start: str) -> ITEvent:
    return ITEvent(id=start or "e", name="e", start_date=start)


def test_event_upcoming_filter():
    soon = _event("2026-08-05")
    far = _event("2026-11-30")
    past = _event("2026-01-10")
    kept = event_registry._upcoming([soon, far, past], days=30)
    assert kept == [soon], f"expected only the upcoming event, got {kept}"
    assert event_registry._upcoming([soon, far, past], days=0) == [soon, far, past]
    print("ok test_event_upcoming_filter")


def test_saved_store():
    tmp = tempfile.mkdtemp()
    original = saved_store.SAVED_FILE
    saved_store.SAVED_FILE = os.path.join(tmp, "saved.json")
    try:
        assert saved_store.all_saved() == {"tenders": [], "partners": [], "leads": []}
        assert saved_store.save_item("tenders", "T-001")["already_saved"] is False
        assert saved_store.save_item("tenders", "T-001")["already_saved"] is True
        assert saved_store.is_saved("tenders", "T-001") is True
        assert saved_store.is_saved("tenders", "T-002") is False
        assert saved_store.list_saved("tenders") == ["T-001"]
        assert saved_store.save_item("unknown", "X")["ok"] is False
        assert saved_store.remove_item("tenders", "T-001")["was_saved"] is True
        assert saved_store.remove_item("tenders", "T-001")["was_saved"] is False
        assert saved_store.list_saved("tenders") == []
    finally:
        saved_store.SAVED_FILE = original
    print("ok test_saved_store")


def test_log_capture():
    import logging

    from control.runner import _LogCapture

    with _LogCapture() as cap:
        logging.getLogger("control.test").info("hello capture")
    assert "hello capture" in cap.text
    assert "INFO" in cap.text
    print("ok test_log_capture")


if __name__ == "__main__":
    test_tender_recent_filter()
    test_tender_fetch_applies_filter()
    test_event_upcoming_filter()
    test_saved_store()
    test_log_capture()
    print("\nALL CONTROL TESTS PASSED")
