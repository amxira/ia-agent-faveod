"""Faveod Assist - the chat agent (Task 6.2).

A tool-calling loop on top of the shared LLM client:
1. the model picks a tool (JSON action) -> we execute it against the agents,
2. the tool result is fed back as JSON,
3. the model produces the final answer.

If the LLM is unavailable (rate limit / no key), local fallback answers keep
the chat functional.
"""

from __future__ import annotations

import json
import logging

from chat.fallback import _format_result, local_answer
from chat.prompts import SYSTEM_PROMPT, build_user_prompt
from chat.tools import TOOLS
from tender_hunter.llm.client import LLMClient

log = logging.getLogger(__name__)

_MAX_TOOL_RESULT_CHARS = 6000


class ChatAssistant:
    """Stateful assistant: keeps the conversation and executes tools."""

    def __init__(self, llm: LLMClient | None = None):
        # Fast-fail for the chat: one attempt, then the local fallback takes
        # over instead of making the user wait through long retry loops.
        self.llm = llm or LLMClient(timeout=30, max_retries=1)
        self.history: list[dict] = []

    @property
    def messages(self) -> list[dict]:
        """User/assistant turns only (what the UI should render)."""
        return [m for m in self.history if m.get("role") in ("user", "assistant")]

    def answer(self, message: str, max_steps: int = 5) -> str:
        """Process one user message and return the assistant's reply."""
        self.history.append({"role": "user", "content": message})
        transcript = self.history[-12:]
        seen_calls: set[tuple] = set()
        last_result: dict | None = None

        def finish(text: str) -> str:
            self.history.append({"role": "assistant", "content": text})
            return text

        for _ in range(max_steps):
            raw = self.llm.chat_json(SYSTEM_PROMPT, build_user_prompt(transcript))
            if raw is None:
                return finish(local_answer(message, transcript))

            answer = raw.get("answer")
            if isinstance(answer, str) and answer.strip():
                return finish(answer.strip())

            tool = raw.get("tool")
            if isinstance(tool, str) and tool in TOOLS:
                arguments = raw.get("arguments") or {}
                if not isinstance(arguments, dict):
                    arguments = {}
                signature = (tool, tuple(sorted(arguments.items())))
                try:
                    result = TOOLS[tool](**arguments)
                except TypeError as exc:
                    result = {"ok": False, "error": f"arguments invalides : {exc}"}
                log.info("chat tool %r -> %s", tool, str(result)[:200])
                self.history.append(
                    {
                        "role": "tool",
                        "name": tool,
                        "content": json.dumps(result, ensure_ascii=False, default=str)[:_MAX_TOOL_RESULT_CHARS],
                    }
                )
                if signature in seen_calls:
                    # The model is looping on the same call; answer from the result.
                    return finish(_format_result(result))
                seen_calls.add(signature)
                last_result = result
                continue

            return finish(local_answer(message, transcript))

        if last_result is not None:
            return finish(_format_result(last_result))
        return finish("Je n'ai pas pu terminer cette requête après plusieurs étapes. Reformulez-la, merci.")
