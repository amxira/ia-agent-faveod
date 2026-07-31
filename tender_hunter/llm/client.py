"""OpenAI-compatible chat client pointed at OpenRouter (free reasoning models)."""

from __future__ import annotations

import json
import logging
import re

import requests

from openai import OpenAI

from tender_hunter import config

log = logging.getLogger(__name__)

# When the configured free model disappears (common on OpenRouter), prefer a
# free reasoning-class model from this ordering, then any other free model.
# Safety/guard/vision models are excluded - they are useless for JSON analysis.
_FREE_MODEL_PREFERENCE = (
    "reasoning",
    "omni",
    "nemotron-3-super",
    "gpt-oss",
    "gemma",
    "deepseek",
    "nemotron",
    "ling",
)
_BANNED_MODELS = ("content-safety", "safety", "guard", "nano-vl", "vision")


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


def discover_free_model() -> str | None:
    """Find a currently free model on OpenRouter (best-effort)."""
    try:
        resp = requests.get("https://openrouter.ai/api/v1/models", timeout=20)
        resp.raise_for_status()
        free = [
            m["id"]
            for m in resp.json().get("data", [])
            if str(m.get("id", "")).endswith(":free")
            and not any(banned in str(m.get("id", "")) for banned in _BANNED_MODELS)
        ]
        for tag in _FREE_MODEL_PREFERENCE:
            for mid in free:
                if tag in mid:
                    return mid
        return free[0] if free else None
    except Exception as exc:  # noqa: BLE001
        log.warning("free-model discovery failed: %s", exc)
        return None


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None, temperature: float | None = None, timeout: int | None = None):
        self.base_url = base_url if base_url is not None else config.LLM_BASE_URL
        self.api_key = api_key if api_key is not None else config.OPENROUTER_API_KEY
        self.model = model if model is not None else config.LLM_MODEL
        self.temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        self.timeout = timeout if timeout is not None else config.LLM_TIMEOUT
        self._switched_to_free = False

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
                status = getattr(exc, "status_code", None)
                if status == 404 and not self._switched_to_free:
                    replacement = discover_free_model()
                    if replacement and replacement != self.model:
                        log.warning(
                            "model %r unavailable on OpenRouter; auto-switched to free model %r",
                            self.model,
                            replacement,
                        )
                        self.model = replacement
                        self._switched_to_free = True
                        continue
                log.warning("LLM call failed (attempt %d): %s", attempt + 1, exc)
        return None
