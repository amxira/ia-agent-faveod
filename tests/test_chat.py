"""Chat-agent tests (pytest-free).

Run:  python tests/test_chat.py
Covers: the tool-calling loop (tool -> result -> answer), error handling on
bad tool arguments, and the LLM-free local fallback.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chat.assistant import ChatAssistant
from chat.fallback import _detect_agent, local_answer
from chat.tools import _run_without_logs, tool_search_events, tool_search_tenders
from tender_hunter.llm.client import LLMClient


class FakeLLM(LLMClient):
    def __init__(self, responses: list):
        self._responses = responses
        self.calls = 0

    @property
    def available(self) -> bool:
        return True

    def chat_json(self, system: str, user: str) -> dict | None:
        self.calls += 1
        return self._responses.pop(0)


def test_tool_loop():
    llm = FakeLLM([
        {"tool": "dashboard_summary", "arguments": {}},
        {"answer": "Voilà le résumé des agents."},
    ])
    assistant = ChatAssistant(llm)
    reply = assistant.answer("Résume l'état des agents")
    assert reply == "Voilà le résumé des agents."
    roles = [m["role"] for m in assistant.history]
    assert roles == ["user", "tool", "assistant"]
    tool_entry = assistant.history[1]
    assert tool_entry["name"] == "dashboard_summary"
    payload = json.loads(tool_entry["content"])
    assert "tenders" in payload and "partners" in payload
    print("ok test_tool_loop")


def test_bad_arguments_handled():
    llm = FakeLLM([
        {"tool": "save_item", "arguments": {}},
        {"answer": "Il manquait des informations, réessayez."},
    ])
    assistant = ChatAssistant(llm)
    reply = assistant.answer("Enregistre le tender T-001")
    assert reply == "Il manquait des informations, réessayez."
    tool_entry = [m for m in assistant.history if m.get("role") == "tool"][0]
    assert "arguments invalides" in tool_entry["content"]
    print("ok test_bad_arguments_handled")


def test_llm_unavailable_fallback():
    assistant = ChatAssistant(LLMClient(api_key=""))
    reply = assistant.answer("Combien de partenaires qualifiés avons-nous ?")
    assert isinstance(reply, str) and reply
    assert "partenaires" in reply.lower() or "agents" in reply.lower() or "état" in reply.lower()
    roles = [m["role"] for m in assistant.history]
    assert roles == ["user", "assistant"]
    print("ok test_llm_unavailable_fallback")


def test_local_answer_intents():
    assert _detect_agent("scanner les appels d'offres") == "tender_hunter"
    assert _detect_agent("trouver des partenaires") == "partner_scout"
    assert _detect_agent("mapping des événements") == "event_mapper"
    assert "résultat" in local_answer("cherche les partenaires")
    assert "résultat" in local_answer("donne moi les leads")
    help_text = local_answer("bonjour")
    assert "Je peux" in help_text
    print("ok test_local_answer_intents")


def test_messages_render_only_visible():
    llm = FakeLLM([
        {"tool": "help", "arguments": {}},
        {"answer": "Voici l'aide."},
    ])
    assistant = ChatAssistant(llm)
    assistant.answer("aide")
    rendered = assistant.messages
    assert [m["role"] for m in rendered] == ["user", "assistant"], rendered
    assert all("content" in m for m in rendered)
    print("ok test_messages_render_only_visible")


def test_events_search_and_intent():
    result = tool_search_events(limit=10)
    assert "items" in result and "count" in result
    reply = local_answer("donne moi le meilleur events")
    assert "résultat" in reply or "Aucun" in reply
    assert "Événement" in reply or "événement" in reply or "Aucun" in reply
    print("ok test_events_search_and_intent")


def test_run_tool_strips_log():
    res = _run_without_logs(lambda: {"log": "secret-log", "ok": True})
    assert res == {"ok": True}, res
    print("ok test_run_tool_strips_log")


def test_per_country_grouping():
    result = tool_search_events(per_country=True, limit=20)
    assert result.get("grouped") is True
    countries = [i.get("country") for i in result["items"]]
    assert len(countries) == len(set(countries)), "one event per country expected"
    assert result["count"] >= 1
    assert "Meilleur par pays" in local_answer("donne moi le meilleur event pour chaque pays")
    print("ok test_per_country_grouping")


def test_meta_words_do_not_filter():
    result = tool_search_events(query="best", limit=10)
    assert result["count"] >= 1, "query 'best' must not filter events out"
    assert tool_search_tenders(query="top tenders", limit=10)["count"] >= 0
    print("ok test_meta_words_do_not_filter")


if __name__ == "__main__":
    test_tool_loop()
    test_bad_arguments_handled()
    test_llm_unavailable_fallback()
    test_local_answer_intents()
    test_messages_render_only_visible()
    test_events_search_and_intent()
    test_run_tool_strips_log()
    test_per_country_grouping()
    test_meta_words_do_not_filter()
    print("\nALL CHAT TESTS PASSED")
