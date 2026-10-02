"""HuggingFace Inference Providers adapter.

Talks the **OpenAI-compatible** chat completions API exposed by the HuggingFace
router (``POST {base_url}/chat/completions``) instead of the task endpoint
(``/hf-inference/models/{model}``).

Why the change: the task endpoint is pinned to a single provider and rejects most
current models with ``Model not supported by provider hf-inference``. The router's
chat endpoint selects a provider that actually serves the requested model, routes
between them, and answers in the OpenAI shape - which our ``first_text`` already
understands, so the two model vendors share one response parser.
"""

from __future__ import annotations

import httpx

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightRequest, InsightResult
from tv_insight.domain.text import truncate
from tv_insight.infrastructure.ai.base import HttpInsightProvider, first_text

MAX_TOKENS = 220
TEMPERATURE = 0.6


class HuggingFaceInsightProvider(HttpInsightProvider):
    """Generates insights through the HuggingFace Inference Providers router."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_token: str,
        model: str,
        base_url: str = "https://router.huggingface.co/v1",
        timeout_seconds: float = 20.0,
        max_retries: int = 1,
    ) -> None:
        super().__init__(client, timeout_seconds=timeout_seconds, max_retries=max_retries)
        self._token = api_token.strip()
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "huggingface"

    @property
    def model(self) -> str:
        """Reported by ``/api/health`` so a stale model id is visible at a glance."""
        return self._model

    def is_available(self) -> bool:
        return bool(self._token)

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        del refresh  # caching is handled one layer above
        if not self.is_available():
            raise ProviderUnavailable("huggingface: HUGGINGFACE_API_TOKEN is not set")

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": request.prompt.system},
                {"role": "user", "content": request.prompt.user},
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        }
        data = await self._post_json(
            f"{self._base_url}/chat/completions",
            payload=payload,
            headers={"Authorization": f"Bearer {self._token}"},
        )

        text = first_text(data)
        cleaned = " ".join(text.split()) if text else ""
        if not cleaned:
            # Naming the model matters here: reasoning-style models can answer 200
            # with an empty `content`, and the operator needs to know which one.
            raise ProviderUnavailable(
                f"huggingface: model {self._model} returned an empty completion"
            )

        return InsightResult(text=truncate(cleaned, 600), provider=self.name)
