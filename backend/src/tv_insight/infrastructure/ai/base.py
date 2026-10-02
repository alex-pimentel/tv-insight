"""Shared plumbing for HTTP based providers."""

from __future__ import annotations

from typing import Any

import httpx

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightProvider
from tv_insight.infrastructure.logging import get_logger
from tv_insight.infrastructure.resilience import retrying_call

logger = get_logger(__name__)

RATE_LIMITED = httpx.codes.TOO_MANY_REQUESTS


class HttpInsightProvider(InsightProvider):
    """Base class holding the HTTP concerns: timeout, retry, error mapping.

    A rate limited or broken upstream is *not* retried in a loop. It is reported
    as ``ProviderUnavailable`` immediately so the fallback chain can move to the
    next provider - for an interactive screen, degrading fast beats waiting.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
    ) -> None:
        self._client = client
        self._timeout = timeout_seconds
        self._max_retries = max(max_retries, 0)

    async def _post_json(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        async def attempt() -> httpx.Response:
            return await self._client.post(
                url,
                json=payload,
                headers=headers or {},
                timeout=self._timeout,
            )

        try:
            response = await retrying_call(attempt, attempts=self._max_retries + 1)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"{self.name}: transport failure ({exc})") from exc

        if response.status_code == RATE_LIMITED:
            raise ProviderUnavailable(f"{self.name}: rate limited (429)")
        if response.status_code >= httpx.codes.BAD_REQUEST:
            detail = _short(response)
            raise ProviderUnavailable(
                f"{self.name}: HTTP {response.status_code} {detail}".strip()
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ProviderUnavailable(f"{self.name}: response was not JSON") from exc


def _short(response: httpx.Response) -> str:
    try:
        body = response.text.strip().replace("\n", " ")
    except Exception:  # pragma: no cover - defensive
        return ""
    return body[:180]


def first_text(candidate: Any) -> str | None:
    """Pull the generated text out of the common response shapes.

    Both vendors speak the OpenAI chat shape
    (``{"choices": [{"message": {"content": ...}}]}``). The HuggingFace *task*
    shape (``[{"generated_text": ...}]``) is still accepted, because it costs
    nothing and keeps the extraction logic tolerant of a provider redirecting to a
    task-style endpoint. Accepting both keeps extraction in one tested place.
    """
    if isinstance(candidate, dict):
        choices = candidate.get("choices")
        if isinstance(choices, list) and choices:
            first_choice = choices[0]
            if isinstance(first_choice, dict):
                message = first_choice.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, str):
                        return content
                text = first_choice.get("text")
                if isinstance(text, str):
                    return text
        generated = candidate.get("generated_text")
        if isinstance(generated, str):
            return generated
        return None

    if isinstance(candidate, list):
        for item in candidate:
            if isinstance(item, dict):
                generated = item.get("generated_text")
                if isinstance(generated, str):
                    return generated
            elif isinstance(item, str):
                return item
    return None
