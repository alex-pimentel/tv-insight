"""Level 3: os caminhos de degradação da IA que os testes de caminho feliz não tocam.

Falha de transporte num provider, credencial ausente no momento da chamada, e os
ramos do gerador determinístico. São exatamente as linhas que a cobertura apontava
como descobertas — e são os cenários que acontecem em produção.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import InsightRequest
from tv_insight.domain.services.insight_prompt import InsightPrompt, InsightSubject
from tv_insight.domain.value_objects import ContentTarget
from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider
from tv_insight.infrastructure.ai.huggingface import HuggingFaceInsightProvider
from tv_insight.infrastructure.ai.openrouter import OpenRouterInsightProvider
from tv_insight.infrastructure.cache import AsyncTtlCache

HF_BASE = "https://hf.edge.test/v1"
OR_BASE = "https://or.edge.test/api/v1"
MODEL = "some/model"


def request(
    *,
    target: ContentTarget = ContentTarget.SERIES,
    title: str = "Breaking Bad",
    summary: str = "A chemistry teacher turns to crime.",
    genres: tuple[str, ...] = ("Drama", "Crime"),
    comments: tuple[str, ...] = (),
    series_name: str | None = None,
    episode_code: str | None = None,
) -> InsightRequest:
    subject = InsightSubject(
        target=target,
        title=title,
        summary=summary,
        genres=genres,
        comments=comments,
        series_name=series_name,
        episode_code=episode_code,
    )
    return InsightRequest(prompt=InsightPrompt(system="S", user="U"), subject=subject)


@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=1.0)


class TestTransportFailures:
    @respx.mock
    async def test_huggingface_transport_error_becomes_provider_unavailable(
        self, client: httpx.AsyncClient
    ) -> None:
        respx.post(f"{HF_BASE}/chat/completions").mock(
            side_effect=httpx.ConnectError("no route")
        )
        provider = HuggingFaceInsightProvider(
            client, api_token="t", model=MODEL, base_url=HF_BASE, max_retries=0
        )

        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(request())

        assert "transport failure" in str(error.value)

    @respx.mock
    async def test_openrouter_transport_error_becomes_provider_unavailable(
        self, client: httpx.AsyncClient
    ) -> None:
        respx.post(f"{OR_BASE}/chat/completions").mock(
            side_effect=httpx.ReadTimeout("too slow")
        )
        provider = OpenRouterInsightProvider(
            client, api_key="k", model=MODEL, base_url=OR_BASE, max_retries=0
        )

        with pytest.raises(ProviderUnavailable):
            await provider.generate(request())


class TestCredentialsCheckedAtCallTime:
    async def test_openrouter_without_a_key_refuses_to_call(
        self, client: httpx.AsyncClient
    ) -> None:
        provider = OpenRouterInsightProvider(client, api_key="", model=MODEL, base_url=OR_BASE)

        assert provider.is_available() is False
        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(request())

        assert "OPENROUTER_API_KEY" in str(error.value)

    async def test_huggingface_without_a_token_refuses_to_call(
        self, client: httpx.AsyncClient
    ) -> None:
        provider = HuggingFaceInsightProvider(client, api_token="", model=MODEL, base_url=HF_BASE)

        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(request())

        assert "HUGGINGFACE_API_TOKEN" in str(error.value)


class TestHeuristicBranches:
    @pytest.mark.parametrize(
        "genres",
        [("Drama",), ("Drama", "Crime"), ("Drama", "Crime", "Thriller"), ()],
    )
    async def test_every_genre_combination_produces_prose(
        self, genres: tuple[str, ...]
    ) -> None:
        result = await HeuristicInsightProvider().generate(request(genres=genres))

        assert result.text.strip()
        assert len(result.text.split()) <= 60
        assert result.degraded is True

    async def test_a_missing_summary_is_not_mentioned(self) -> None:
        result = await HeuristicInsightProvider().generate(request(summary=""))

        assert "not available" not in result.text
        assert result.text.strip()

    async def test_a_comment_is_quoted_when_present(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(comments=("The pacing is perfect",))
        )
        assert "The pacing is perfect" in result.text

    async def test_a_very_long_summary_is_shortened(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(summary="word " * 400)
        )
        assert len(result.text.split()) <= 60

    async def test_a_very_long_comment_is_shortened(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(comments=("x" * 500,))
        )
        assert len(result.text.split()) <= 60

    async def test_episode_without_series_name_still_reads_well(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(target=ContentTarget.EPISODE, title="Grilled", series_name=None)
        )
        assert "Grilled" in result.text


class TestHeuristicCommunityThemes:
    """The heuristic only claims a recurring theme when a word really repeats."""

    async def test_a_repeated_word_becomes_a_theme(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(
                comments=(
                    "The pacing of this show is remarkable",
                    "Pacing aside, the acting carries it",
                )
            )
        )

        assert "2 community comments" in result.text
        assert "pacing" in result.text

    async def test_no_theme_is_claimed_when_nothing_repeats(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(comments=("Loved the cinematography", "Too slow at times"))
        )

        assert "community comments so far" in result.text

    async def test_a_single_comment_becomes_an_example(self) -> None:
        result = await HeuristicInsightProvider().generate(
            request(comments=("A masterpiece of television",))
        )

        assert "1 community comments" in result.text
        assert "masterpiece" in result.text

    async def test_no_comments_means_no_community_sentence(self) -> None:
        result = await HeuristicInsightProvider().generate(request(comments=()))

        assert "community comments" not in result.text

    @pytest.mark.parametrize(
        "comments",
        [
            ("", "   "),
            ("the the the the",),
            ("a", "an"),
        ],
    )
    async def test_degenerate_comments_do_not_break_the_heuristic(
        self, comments: tuple[str, ...]
    ) -> None:
        result = await HeuristicInsightProvider().generate(request(comments=comments))

        assert result.text.strip()
        assert len(result.text.split()) <= 60

    async def test_the_theme_list_never_grows_unbounded(self) -> None:
        comments = tuple(f"repeated word{index} appears here" for index in range(20))
        result = await HeuristicInsightProvider().generate(request(comments=comments))

        assert len(result.text.split()) <= 60


class TestCompositeDelegation:
    def test_the_chain_name_lists_its_tiers(self) -> None:
        chain = FallbackInsightProvider(
            [HeuristicInsightProvider(), HeuristicInsightProvider()]
        )
        assert chain.name.startswith("fallback[heuristic")


class TestCachingDelegation:
    def test_the_decorator_reports_the_inner_identity(self) -> None:
        inner = HeuristicInsightProvider()
        provider = CachingInsightProvider(inner, AsyncTtlCache(60))

        assert provider.name == "heuristic"
        assert provider.is_available() is True
        assert provider.inner is inner
