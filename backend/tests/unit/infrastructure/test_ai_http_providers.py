"""Level 3: the HTTP AI providers, their payloads and their error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightRequest
from tv_insight.domain.services.insight_prompt import InsightPrompt, InsightSubject
from tv_insight.domain.value_objects import ContentTarget
from tv_insight.infrastructure.ai.base import first_text
from tv_insight.infrastructure.ai.huggingface import HuggingFaceInsightProvider
from tv_insight.infrastructure.ai.openrouter import OpenRouterInsightProvider

HF_BASE = "https://hf.test/v1"
OR_BASE = "https://openrouter.test/api/v1"
MODEL = "some/model"


def request() -> InsightRequest:
    return InsightRequest(
        prompt=InsightPrompt(system="SYSTEM", user="USER"),
        subject=InsightSubject(
            target=ContentTarget.SERIES, title="Show", summary="Summary"
        ),
    )


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=1.0)


class TestHuggingFace:
    """The adapter uses the router's OpenAI-compatible chat completions endpoint.

    The task endpoint (`/hf-inference/models/{model}`) is pinned to a single
    provider and rejects most current models, so the router endpoint - which picks
    a provider that serves the model - is the one under contract here.
    """

    def provider(self, client: httpx.AsyncClient, token: str = "hf-token"):
        return HuggingFaceInsightProvider(
            client, api_token=token, model=MODEL, base_url=HF_BASE, max_retries=0
        )

    def test_is_unavailable_without_a_token(self, client: httpx.AsyncClient) -> None:
        assert self.provider(client, token="").is_available() is False

    async def test_missing_token_short_circuits(
        self, client: httpx.AsyncClient
    ) -> None:
        provider = self.provider(client, token="")

        with pytest.raises(ProviderUnavailable):
            await provider.generate(request())

    @respx.mock
    async def test_sends_an_openai_shaped_chat_request(
        self, client: httpx.AsyncClient
    ) -> None:
        route = respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": " An insight. "}}]}
            )
        )

        result = await self.provider(client).generate(request())

        assert result.text == "An insight."
        assert result.provider == "huggingface"
        assert result.degraded is False

        sent = route.calls[0].request
        assert sent.headers["authorization"] == "Bearer hf-token"
        body = sent.content.decode()
        assert f'"model":"{MODEL}"' in body
        assert '"role":"system"' in body
        assert '"role":"user"' in body
        assert '"max_tokens"' in body

    @respx.mock
    async def test_it_does_not_use_the_task_endpoint(self, client: httpx.AsyncClient) -> None:
        # Guard against a regression to `/hf-inference/models/{model}`, which is
        # what produced "Model not supported by provider hf-inference".
        chat = respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        )
        legacy = respx.post(f"{HF_BASE}/{MODEL}").mock(
            return_value=httpx.Response(400, json={"error": "Model not supported"})
        )

        await self.provider(client).generate(request())

        assert chat.called is True
        assert legacy.called is False

    @respx.mock
    async def test_a_task_style_response_is_still_understood(
        self, client: httpx.AsyncClient
    ) -> None:
        # `first_text` is shared with OpenRouter and tolerates both shapes.
        respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(200, json=[{"generated_text": "Task style."}])
        )

        result = await self.provider(client).generate(request())

        assert result.text == "Task style."

    @respx.mock
    async def test_empty_completion_names_the_model(
        self, client: httpx.AsyncClient
    ) -> None:
        # Reasoning-style models can answer 200 with a null `content`; the message
        # must say which model so the operator can switch it.
        respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(
                200,
                json={"choices": [{"message": {"content": None, "reasoning_content": "..."}}]},
            )
        )

        with pytest.raises(ProviderUnavailable) as error:
            await self.provider(client).generate(request())

        assert MODEL in str(error.value)

    @respx.mock
    async def test_an_unsupported_model_error_surfaces_the_upstream_message(
        self, client: httpx.AsyncClient
    ) -> None:
        respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(
                400,
                json={
                    "error": {
                        "message": f"The requested model '{MODEL}' is not supported",
                        "code": "model_not_supported",
                    }
                },
            )
        )

        with pytest.raises(ProviderUnavailable) as error:
            await self.provider(client).generate(request())

        assert "model_not_supported" in str(error.value) or "not supported" in str(error.value)

    @respx.mock
    async def test_rate_limit_is_reported_immediately(
        self, client: httpx.AsyncClient
    ) -> None:
        route = respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(429, text="slow down")
        )

        with pytest.raises(ProviderUnavailable) as error:
            await self.provider(client).generate(request())

        assert "rate limited" in str(error.value)
        assert route.call_count == 1

    @respx.mock
    async def test_server_error_is_reported(self, client: httpx.AsyncClient) -> None:
        respx.post(f"{HF_BASE}/chat/completions").mock(return_value=httpx.Response(503))

        with pytest.raises(ProviderUnavailable):
            await self.provider(client).generate(request())

    @respx.mock
    async def test_invalid_json_is_reported(self, client: httpx.AsyncClient) -> None:
        respx.post(f"{HF_BASE}/chat/completions").mock(
            return_value=httpx.Response(200, text="<html>")
        )

        with pytest.raises(ProviderUnavailable):
            await self.provider(client).generate(request())


class TestOpenRouter:
    def provider(self, client: httpx.AsyncClient, key: str = "or-key"):
        return OpenRouterInsightProvider(
            client,
            api_key=key,
            model=MODEL,
            base_url=OR_BASE,
            site_url="http://site.test",
            app_name="tv-insight",
            max_retries=0,
        )

    def test_is_unavailable_without_a_key(self, client: httpx.AsyncClient) -> None:
        assert self.provider(client, key="").is_available() is False

    @respx.mock
    async def test_sends_a_chat_completion_request(
        self, client: httpx.AsyncClient
    ) -> None:
        route = respx.post(f"{OR_BASE}/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": "Hello."}}]}
            )
        )

        result = await self.provider(client).generate(request())

        assert result.text == "Hello."
        assert result.provider == "openrouter"
        body = route.calls[0].request.content.decode()
        assert '"role":"system"' in body
        assert '"role":"user"' in body
        assert MODEL in body

    @respx.mock
    async def test_auth_header_is_sent(self, client: httpx.AsyncClient) -> None:
        route = respx.post(f"{OR_BASE}/chat/completions").mock(
            return_value=httpx.Response(
                200, json={"choices": [{"message": {"content": "ok"}}]}
            )
        )

        await self.provider(client).generate(request())

        headers = route.calls[0].request.headers
        assert headers["authorization"] == "Bearer or-key"
        assert headers["x-title"] == "tv-insight"

    @respx.mock
    async def test_error_status_is_reported(self, client: httpx.AsyncClient) -> None:
        respx.post(f"{OR_BASE}/chat/completions").mock(
            return_value=httpx.Response(402, text="no credits")
        )

        with pytest.raises(ProviderUnavailable) as error:
            await self.provider(client).generate(request())

        assert "402" in str(error.value)

    @respx.mock
    async def test_empty_choices_is_a_failure(self, client: httpx.AsyncClient) -> None:
        respx.post(f"{OR_BASE}/chat/completions").mock(
            return_value=httpx.Response(200, json={"choices": []})
        )

        with pytest.raises(ProviderUnavailable):
            await self.provider(client).generate(request())


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([{"generated_text": "task shape"}], "task shape"),
        ({"choices": [{"message": {"content": "chat shape"}}]}, "chat shape"),
        ({"generated_text": "flat"}, "flat"),
        ({"choices": [{"text": "completion"}]}, "completion"),
        (["bare string"], "bare string"),
        ({"choices": []}, None),
        ({}, None),
        (None, None),
        (123, None),
    ],
)
def test_first_text_understands_every_supported_shape(
    payload: object, expected: str | None
) -> None:
    assert first_text(payload) == expected
