"""In-memory chat session store for the REST API.

The `ChatAssistant` is stateful (it keeps its conversation history), so each
frontend conversation is pinned to a `session_id`. Sessions live in memory: they
are lost when the API restarts, which is fine for a self-hosted internal tool.
A future upgrade could persist them to `data/state/chat_sessions.json`.
"""

from __future__ import annotations

import threading
import uuid

from chat.assistant import ChatAssistant


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatAssistant] = {}
        self._lock = threading.Lock()

    def create(self) -> tuple[str, ChatAssistant]:
        session_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._sessions[session_id] = ChatAssistant()
        return session_id, self._sessions[session_id]

    def get(self, session_id: str) -> ChatAssistant | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None) -> tuple[str, ChatAssistant]:
        if session_id and (assistant := self.get(session_id)):
            return session_id, assistant
        return self.create()

    def drop(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None


sessions = SessionStore()
