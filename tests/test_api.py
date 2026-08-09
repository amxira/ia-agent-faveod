"""REST API tests (pytest-free).

Run:  python tests/test_api.py
Covers: health/summary/options, the four data feeds + detail lookups, the
favorites store through HTTP, 404s, and the chat endpoint (LLM stubbed so the
test never touches the network or a real agent run).
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

import importlib

api_module = importlib.import_module("api.app")

from chat.assistant import ChatAssistant
from tender_hunter.llm.client import LLMClient

client = TestClient(api_module.app)


class FakeLLM(LLMClient):
    def __init__(self, responses: list):
        self._responses = responses

    @property
    def available(self) -> bool:
        return True

    def chat_json(self, system: str, user: str) -> dict | None:
        return self._responses.pop(0)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    print("ok test_health")


def test_agent_options():
    body = client.get("/api/agents/options").json()
    assert "tender_sources" in body and "world_bank" in body["tender_sources"]
    assert "partner_sources" in body and "searxng" in body["partner_sources"]
    assert "event_sources" in body and "ten_times" in body["event_sources"]
    assert "countries" in body and "Morocco" in body["countries"]
    print("ok test_agent_options")


def test_summary():
    body = client.get("/api/summary").json()
    for key in ("tenders", "high_value_tenders", "partners", "qualified_partners",
                "events", "leads", "priority_leads", "saved"):
        assert key in body, f"missing {key}"
    assert body["tenders"] >= 1
    print("ok test_summary")


def test_tenders_list_and_detail():
    listing = client.get("/api/tenders?min_score=0&limit=5").json()
    assert listing["count"] >= 1 and listing["items"]
    first = listing["items"][0]
    assert "tender_id" in first and "fit_score" in first

    detail = client.get(f"/api/tenders/{first['tender_id']}").json()
    assert detail["tender_id"] == first["tender_id"]

    assert client.get("/api/tenders?min_score=10000").status_code in (200, 422)
    assert client.get("/api/tenders/NOPE-999").status_code == 404
    print("ok test_tenders_list_and_detail")


def test_partners_list_and_detail():
    listing = client.get("/api/partners?qualified_only=true&limit=5").json()
    assert listing["count"] >= 0
    all_partners = client.get("/api/partners?limit=50").json()
    assert all_partners["count"] >= 1
    first = all_partners["items"][0]
    detail = client.get(f"/api/partners/{first['partner_id']}").json()
    assert detail["partner_id"] == first["partner_id"]
    assert client.get("/api/partners/NOPE-999").status_code == 404
    print("ok test_partners_list_and_detail")


def test_events_and_leads():
    events = client.get("/api/events?upcoming_days=0&limit=10").json()
    assert events["count"] >= 1
    first_event = events["items"][0]
    assert "lead_count" in first_event

    leads = client.get("/api/leads?priority=HIGH PRIORITY&limit=10").json()
    assert leads["count"] >= 1
    first_lead = leads["items"][0]
    detail = client.get(f"/api/leads/{first_lead['lead_id']}").json()
    assert detail["lead_id"] == first_lead["lead_id"]
    assert client.get("/api/leads/NOPE-999").status_code == 404
    print("ok test_events_and_leads")


def test_favorites_flow():
    tmp = tempfile.mkdtemp()
    import control.saved as saved_module

    original = saved_module.SAVED_FILE
    saved_module.SAVED_FILE = os.path.join(tmp, "saved.json")
    api_module.app.state._saved_patched = True
    try:
        listing = client.get("/api/tenders?limit=1").json()
        tid = listing["items"][0]["tender_id"]

        saved = client.get("/api/saved").json()
        assert saved["tenders"]["count"] == 0

        assert client.post(f"/api/saved/tenders/{tid}").json()["ok"] is True
        assert client.post(f"/api/saved/tenders/{tid}").json()["already_saved"] is True
        saved = client.get("/api/saved").json()
        assert saved["tenders"]["count"] == 1
        assert saved["tenders"]["items"][0]["tender_id"] == tid

        assert client.post("/api/saved/bogus/X").status_code == 422
        assert client.delete(f"/api/saved/tenders/{tid}").json()["was_saved"] is True
        assert client.get("/api/saved").json()["tenders"]["count"] == 0
    finally:
        saved_module.SAVED_FILE = original
    print("ok test_favorites_flow")


def test_chat_with_stubbed_llm():
    class FakeStore:
        def __init__(self):
            self.sid = "test-session"
            self.assistant = ChatAssistant(FakeLLM([
                {"tool": "dashboard_summary", "arguments": {}},
                {"answer": "Voilà le résumé des agents."},
            ]))

        def get_or_create(self, session_id):
            return self.sid, self.assistant

    original = api_module.sessions
    api_module.sessions = FakeStore()
    try:
        body = client.post("/api/chat", json={"message": "Résume l'état"}).json()
        assert body["session_id"] == "test-session"
        assert body["reply"] == "Voilà le résumé des agents."
        roles = [m["role"] for m in body["history"]]
        assert roles == ["user", "tool", "assistant"]
    finally:
        api_module.sessions = original
    print("ok test_chat_with_stubbed_llm")


if __name__ == "__main__":
    test_health()
    test_agent_options()
    test_summary()
    test_tenders_list_and_detail()
    test_partners_list_and_detail()
    test_events_and_leads()
    test_favorites_flow()
    test_chat_with_stubbed_llm()
    print("\nALL API TESTS PASSED")
