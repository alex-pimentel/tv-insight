"""OpenRouter provider (OpenAI compatible chat completions)."""

from __future__ import annotations

from typing import Any

import httpx

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightRequest, InsightResult
from tv_insight.domain.text import truncate
from tv_insight.infrastructure.ai.base import HttpInsightProvider, first_text

MAX_TOKENS = 220


class OpenRouterInsightProvider(HttpInsightProvider):
    """Talks the OpenAI chat-completions dialect against OpenRouter."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        site_url: str = "http://localhost:7777",
        app_name: str = "tv-insight",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
    ) -> None:
        super().__init__(client, timeout_seconds=timeout_seconds, max_retries=max_retries)
        self._key = api_key.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._site_url = site_url
        self._app_name = app_name

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        """Reported by ``/api/health`` so the configured model is visible."""
        return self._model

    def is_available(self) -> bool:
        return bool(self._key)

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        del refresh
        if not self.is_available():
            raise ProviderUnavailable("openrouter: OPENROUTER_API_KEY is not set")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.prompt.system},
                {"role": "user", "content": request.prompt.user},
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.6,
        }
        data = await self._post_json(
            f"{self._base_url}/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {self._key}",
                "HTTP-Referer": self._site_url,
                "X-Title": self._app_name,
            },
        )

        text = first_text(data)
        cleaned = " ".join(text.split()) if text else ""
        if not cleaned:
            raise ProviderUnavailable("openrouter: empty completion")

        return InsightResult(text=truncate(cleaned, 600), provider=self.name)
