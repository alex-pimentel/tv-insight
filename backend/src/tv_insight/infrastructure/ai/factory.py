"""Builds the AI provider chain from configuration.

This is the only place that knows the concrete provider names. Adding a vendor is
a new class plus one registry entry - no use case, port or test double changes.

The **default chain reflects the client's guidance** for the fallback strategy:
primary model, then the local heuristic process. A second model vendor is
available but opt-in (``AI_PROVIDER_ORDER=huggingface,openrouter,heuristic``),
so provider independence stays demonstrable without paying for a second LLM tier
by default. See ``docs/CLIENT-FEEDBACK.md``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx

from tv_insight.application.ports.insight import InsightProvider
from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider
from tv_insight.infrastructure.ai.huggingface import HuggingFaceInsightProvider
from tv_insight.infrastructure.ai.openrouter import OpenRouterInsightProvider
from tv_insight.infrastructure.cache import AsyncTtlCache
from tv_insight.infrastructure.config import Settings

ProviderFactory = Callable[[], InsightProvider]

#: Provider that must always close the chain, so an insight is always produced.
TERMINAL_PROVIDER = "heuristic"


def build_insight_provider(
    settings: Settings, client: httpx.AsyncClient
) -> InsightProvider:
    registry: dict[str, ProviderFactory] = {
        "huggingface": lambda: HuggingFaceInsightProvider(
            client,
            api_token=settings.huggingface_api_token,
            model=settings.huggingface_model,
            base_url=settings.huggingface_base_url,
            timeout_seconds=settings.ai_timeout_seconds,
        ),
        "openrouter": lambda: OpenRouterInsightProvider(
            client,
            api_key=settings.openrouter_api_key,
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            site_url=settings.openrouter_site_url,
            app_name=settings.openrouter_app_name,
            timeout_seconds=settings.ai_timeout_seconds,
        ),
        "heuristic": HeuristicInsightProvider,
    }

    selected = [name for name in settings.provider_order if name in registry]
    # The terminal provider always runs, and always last.
    if TERMINAL_PROVIDER not in selected:
        selected.append(TERMINAL_PROVIDER)
    selected = [name for name in selected if name != TERMINAL_PROVIDER] + [TERMINAL_PROVIDER]

    chain = FallbackInsightProvider([registry[name]() for name in selected])
    cache: AsyncTtlCache[str, object] = AsyncTtlCache(
        ttl_seconds=settings.ai_insight_cache_ttl_seconds
    )
    return CachingInsightProvider(chain, cache)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ProviderInfo:
    """One tier of the chain, as reported by the health endpoint."""

    name: str
    available: bool
    #: The configured model, when the provider has one. Surfacing it here is what
    #: makes a stale model id obvious without reading the environment.
    model: str | None = None


def describe_providers(provider: InsightProvider) -> list[ProviderInfo]:
    """Flatten the decorator stack into provider metadata.

    Used by the health endpoint so an operator can see, without reading logs,
    which tiers of the chain are usable and which model each one will call.
    """
    target: object = provider
    while isinstance(target, CachingInsightProvider):
        target = target.inner

    if isinstance(target, FallbackInsightProvider):
        return [_info(item) for item in target.providers]
    if isinstance(target, InsightProvider):
        return [_info(target)]
    return []


def _info(provider: InsightProvider) -> ProviderInfo:
    # Only the HTTP vendors have a model; the heuristic has nothing to configure.
    model = getattr(provider, "model", None)
    return ProviderInfo(
        name=provider.name,
        available=provider.is_available(),
        model=model if isinstance(model, str) else None,
    )
