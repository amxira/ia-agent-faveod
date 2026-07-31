"""OpenAI-compatible chat client pointed at OpenRouter (DeepSeek-R1 free)."""

from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from tender_hunter import config

log = logging.getLogger(__name__)


def _extract_json(text: str) -> dict | None:
    """Tolerantly pull the first balanced JSON object out of a model response."""
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


class LLMClient:
    def __init__(self, base_url: str = "", api_key: str = "", model: str = "", temperature: float = 0.1, timeout: int = 90):
        self.base_url = base_url or config.LLM_BASE_URL
        self.api_key = api_key or config.OPENROUTER_API_KEY
        self.model = model or config.LLM_MODEL
        self.temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        self.timeout = timeout or config.LLM_TIMEOUT

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat_json(self, system: str, user: str) -> dict | None:
        """Return a parsed JSON dict from the model, or None if unavailable/failed."""
        if not self.available:
            log.warning("no LLM API key configured - reasoning engine in guardrail-only mode")
            return None
        client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)

        attempts = config.MAX_LLM_RETRIES + 1
        for attempt in range(attempts):
            try:
                kwargs: dict = {
                    "model": self.model,
                    "temperature": self.temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                }
                if attempt == 0:
                    kwargs["response_format"] = {"type": "json_object"}
                resp = client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content or ""
                parsed = _extract_json(content)
                if parsed is not None:
                    return parsed
                log.warning("model returned non-JSON (attempt %d): %.200s", attempt + 1, content)
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM call failed (attempt %d): %s", attempt + 1, exc)
        return None
