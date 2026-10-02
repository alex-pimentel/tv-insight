"""Level 3: the composition root and the provider factory wiring."""

from __future__ import annotations

import httpx
import pytest

from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.ai.factory import (
    ProviderInfo,
    build_insight_provider,
    describe_providers,
)
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider
from tv_insight.infrastructure.ai.huggingface import HuggingFaceInsightProvider
from tv_insight.infrastructure.ai.openrouter import OpenRouterInsightProvider
from tv_insight.infrastructure.config import Settings


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=1.0)


def test_no_credentials_still_produces_a_working_chain(
    client: httpx.AsyncClient,
) -> None:
    provider = build_insight_provider(Settings(ai_provider_order="huggingface"), client)

    assert isinstance(provider, CachingInsightProvider)
    chain = provider.inner
    assert isinstance(chain, FallbackInsightProvider)
    # The unconfigured vendor stays in the chain (so health can report it) but
    # the offline provider guarantees an answer.
    assert [item.name for item in chain.providers] == ["huggingface", "heuristic"]
    assert chain.is_available() is True


def test_configured_providers_come_before_the_terminal_fallback(
    client: httpx.AsyncClient,
) -> None:
    settings = Settings(
        ai_provider_order="openrouter,huggingface",
        huggingface_api_token="t",
        openrouter_api_key="k",
    )

    provider = build_insight_provider(settings, client)

    assert [info.name for info in describe_providers(provider)] == [
        "openrouter",
        "huggingface",
        "heuristic",
    ]


def test_heuristic_is_forced_last_even_when_listed_first(
    client: httpx.AsyncClient,
) -> None:
    settings = Settings(ai_provider_order="heuristic,openrouter", openrouter_api_key="k")

    provider = build_insight_provider(settings, client)

    assert [info.name for info in describe_providers(provider)][-1] == "heuristic"


def test_unknown_provider_names_are_ignored(client: httpx.AsyncClient) -> None:
    provider = build_insight_provider(
        Settings(ai_provider_order="nope,heuristic"), client
    )

    assert [info.name for info in describe_providers(provider)] == ["heuristic"]


def test_availability_reflects_the_credentials(client: httpx.AsyncClient) -> None:
    provider = build_insight_provider(
        Settings(ai_provider_order="huggingface,openrouter"), client
    )

    availability = {info.name: info.available for info in describe_providers(provider)}

    assert availability == {
        "huggingface": False,
        "openrouter": False,
        "heuristic": True,
    }


def test_the_configured_model_is_reported_for_diagnostics(
    client: httpx.AsyncClient,
) -> None:
    # A stale model id is a real failure mode: `/api/health` has to show it.
    settings = Settings(
        ai_provider_order="huggingface,openrouter",
        huggingface_api_token="t",
        openrouter_api_key="k",
        huggingface_model="meta-llama/Llama-3.1-8B-Instruct",
        openrouter_model="meta-llama/llama-3.1-8b-instruct",
    )

    report = {info.name: info.model for info in describe_providers(
        build_insight_provider(settings, client)
    )}

    assert report == {
        "huggingface": "meta-llama/Llama-3.1-8B-Instruct",
        "openrouter": "meta-llama/llama-3.1-8b-instruct",
        "heuristic": None,
    }


def test_types_are_wired_correctly(client: httpx.AsyncClient) -> None:
    settings = Settings(
        ai_provider_order="huggingface,openrouter",
        huggingface_api_token="t",
        openrouter_api_key="k",
    )

    chain = build_insight_provider(settings, client).inner

    assert isinstance(chain, FallbackInsightProvider)
    assert isinstance(chain.providers[0], HuggingFaceInsightProvider)
    assert isinstance(chain.providers[1], OpenRouterInsightProvider)
    assert isinstance(chain.providers[2], HeuristicInsightProvider)


def test_describe_handles_a_bare_provider(client: httpx.AsyncClient) -> None:
    assert describe_providers(HeuristicInsightProvider()) == [
        ProviderInfo(name="heuristic", available=True)
    ]
