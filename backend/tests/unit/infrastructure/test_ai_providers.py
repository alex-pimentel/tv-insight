"""Level 3: fallback strategy, caching decorator and the offline provider."""

from __future__ import annotations

import pytest

from tests.fakes import (
    RecordingInsightProvider,
    ScriptedInsightProvider,
    UnavailableInsightProvider,
)
from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightRequest
from tv_insight.domain.services.insight_prompt import InsightPrompt, InsightSubject
from tv_insight.domain.value_objects import ContentTarget
from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider
from tv_insight.infrastructure.cache import AsyncTtlCache


def request(**overrides: object) -> InsightRequest:
    subject = InsightSubject(
        target=ContentTarget.SERIES,
        title="Breaking Bad",
        summary="A chemistry teacher turns to crime.",
        genres=("Drama", "Crime"),
        comments=("Superb writing",),
    )
    for key, value in overrides.items():
        object.__setattr__(subject, key, value)
    return InsightRequest(
        prompt=InsightPrompt(system="system", user="user"), subject=subject
    )


class TestFallbackChain:
    async def test_first_available_provider_wins(self) -> None:
        primary = ScriptedInsightProvider(name="primary", answers=("from primary",))
        secondary = ScriptedInsightProvider(name="secondary", answers=("from secondary",))
        chain = FallbackInsightProvider([primary, secondary])

        result = await chain.generate(request())

        assert result.text == "from primary"
        assert result.provider == "primary"
        assert secondary.requests == []

    async def test_falls_through_when_a_provider_fails(self) -> None:
        broken = UnavailableInsightProvider(name="broken")
        healthy = ScriptedInsightProvider(name="healthy", answers=("from healthy",))
        chain = FallbackInsightProvider([broken, healthy])

        result = await chain.generate(request())

        assert broken.attempts == 1
        assert result.text == "from healthy"
        assert result.provider == "healthy"

    async def test_unconfigured_providers_are_skipped(self) -> None:
        skipped = UnavailableInsightProvider(name="skipped", available=False)
        healthy = ScriptedInsightProvider(name="healthy", answers=("ok",))
        chain = FallbackInsightProvider([skipped, healthy])

        result = await chain.generate(request())

        assert skipped.attempts == 0
        assert result.provider == "healthy"

    async def test_degradation_is_explained_in_notes(self) -> None:
        broken = UnavailableInsightProvider(name="broken")
        healthy = ScriptedInsightProvider(name="healthy", answers=("ok",))
        chain = FallbackInsightProvider([broken, healthy])

        result = await chain.generate(request())

        assert any("broken" in note for note in result.notes)

    async def test_unexpected_exception_from_a_provider_is_contained(self) -> None:
        class Exploding(RecordingInsightProvider):
            async def generate(self, request, *, refresh=False):  # noqa: ANN001, ANN202
                raise RuntimeError("kaboom")

        chain = FallbackInsightProvider([Exploding(name="exploding"), HeuristicInsightProvider()])

        result = await chain.generate(request())

        assert result.provider == "heuristic"
        assert result.degraded is True

    async def test_every_provider_failing_raises(self) -> None:
        chain = FallbackInsightProvider(
            [UnavailableInsightProvider(name="a"), UnavailableInsightProvider(name="b")]
        )

        with pytest.raises(ProviderUnavailable) as error:
            await chain.generate(request())

        assert "a" in str(error.value)
        assert "b" in str(error.value)

    async def test_chain_requires_at_least_one_provider(self) -> None:
        with pytest.raises(ValueError):
            FallbackInsightProvider([])

    async def test_is_available_is_true_when_any_tier_is(self) -> None:
        chain = FallbackInsightProvider(
            [UnavailableInsightProvider(available=False), HeuristicInsightProvider()]
        )
        assert chain.is_available() is True


class TestCachingDecorator:
    """A transparent performance layer: the caller cannot tell it is there."""

    async def test_repeated_prompts_hit_the_cache(self) -> None:
        inner = ScriptedInsightProvider(name="inner", answers=("one", "two"))
        provider = CachingInsightProvider(inner, AsyncTtlCache(60))

        first = await provider.generate(request())
        second = await provider.generate(request())

        assert first.text == second.text == "one"
        assert len(inner.requests) == 1

    async def test_refresh_bypasses_the_cache(self) -> None:
        inner = ScriptedInsightProvider(name="inner", answers=("one", "two"))
        provider = CachingInsightProvider(inner, AsyncTtlCache(60))

        await provider.generate(request())
        refreshed = await provider.generate(request(), refresh=True)

        assert refreshed.text == "two"
        assert len(inner.requests) == 2

    async def test_different_prompts_are_cached_separately(self) -> None:
        inner = ScriptedInsightProvider(name="inner", answers=("one", "two"))
        provider = CachingInsightProvider(inner, AsyncTtlCache(60))

        await provider.generate(request())
        await provider.generate(
            InsightRequest(
                prompt=InsightPrompt(system="system", user="different"),
                subject=request().subject,
            )
        )

        assert len(inner.requests) == 2


class TestHeuristicProvider:
    async def test_is_always_available_and_degraded(self) -> None:
        result = await HeuristicInsightProvider().generate(request())

        assert result.provider == "heuristic"
        assert result.degraded is True
        assert result.notes

    async def test_output_mentions_inputs_and_stays_short(self) -> None:
        result = await HeuristicInsightProvider().generate(request())
        text = result.text

        assert "Breaking Bad" in text
        assert "drama and crime" in text
        assert len(text.split()) <= 60

    async def test_episode_subject_is_described_as_an_episode(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(
                target=ContentTarget.EPISODE,
                title="Grilled",
                series_name="Breaking Bad",
                episode_code="S02E02",
            )
        )
        assert "Grilled" in result.text
        assert "Breaking Bad" in result.text
        assert "S02E02" in result.text
        assert "episode" in result.text

    async def test_survives_completely_empty_subject(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(summary="", genres=(), comments=())
        )
        assert result.text.strip()
        assert len(result.text.split()) <= 60

    async def test_is_deterministic(self) -> None:
        provider = HeuristicInsightProvider()
        first = await provider.generate(request())
        second = await provider.generate(request())
        assert first.text == second.text
