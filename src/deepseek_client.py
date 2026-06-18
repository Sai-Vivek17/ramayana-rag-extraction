from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import Settings, get_settings


class DeepSeekError(RuntimeError):
    """Raised when the DeepSeek API call fails or returns unusable output."""


@dataclass
class DeepSeekClient:
    settings: Settings
    logger: logging.Logger | None = None

    @classmethod
    def from_env(cls, logger: logging.Logger | None = None) -> "DeepSeekClient":
        settings = get_settings()
        settings.require_deepseek_key()
        return cls(settings=settings, logger=logger)

    @property
    def endpoint(self) -> str:
        return f"{self.settings.deepseek_base_url}/chat/completions"

    @retry(
        retry=retry_if_exception_type((requests.RequestException, DeepSeekError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def chat_completion(self, messages: list[dict[str, str]], response_format_json: bool = False) -> str:
        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": self.settings.deepseek_temperature,
            "max_tokens": self.settings.deepseek_max_tokens,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        if self.logger:
            self.logger.info("Calling DeepSeek model %s", self.settings.deepseek_model)

        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=120)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise DeepSeekError(f"Temporary DeepSeek API error {response.status_code}")
        if response.status_code >= 400:
            redacted = response.text[:500].replace(self.settings.deepseek_api_key, "[REDACTED]")
            raise DeepSeekError(f"DeepSeek API error {response.status_code}: {redacted}")

        try:
            payload = response.json()
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise DeepSeekError("DeepSeek returned an unexpected response shape.") from exc

    def json_completion(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        content = self.chat_completion(messages, response_format_json=True)
        try:
            return parse_json_response(content)
        except DeepSeekError as original_error:
            if self.logger:
                self.logger.warning("DeepSeek returned malformed JSON; requesting DeepSeek JSON repair.")
            repaired = self.chat_completion(
                [
                    {
                        "role": "system",
                        "content": (
                            "You repair malformed JSON. Return one valid JSON object only. "
                            "Do not add markdown, commentary, or new content. Preserve all source values."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Repair this malformed JSON into strict valid JSON. "
                            "Escape quotes and control characters correctly. JSON to repair:\n\n"
                            f"{content}"
                        ),
                    },
                ],
                response_format_json=True,
            )
            try:
                return parse_json_response(repaired)
            except DeepSeekError:
                raise original_error


def parse_json_response(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    text = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeepSeekError(f"DeepSeek response was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise DeepSeekError("DeepSeek JSON response must be an object.")
    return parsed
