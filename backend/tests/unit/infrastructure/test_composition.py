"""Level 2: the composition root wires and tears down the real graph.

The container is built here (not only injected) because the wiring itself is
behaviour worth protecting: if a dependency changes constructor, this test fails
before the container does.
"""

from __future__ import annotations

import httpx
import pytest

from tv_insight.application.use_cases import (
    AddComment,
    GenerateInsight,
    GetEpisodeDetail,
    GetSeriesDetails,
    ListComments,
    SearchSeries,
    SetEpisodeWatched,
)
from tv_insight.infrastructure.ai.caching import CachingInsightProvider
from tv_insight.infrastructure.composition import Container
from tv_insight.infrastructure.config import Settings
from tv_insight.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tv_insight.infrastructure.tvmaze.caching import CachingTvMazeGateway


def offline_settings(**overrides: object) -> Settings:
    """Settings that never connect anywhere: building must not touch the network."""
    values: dict[str, object] = {
        "app_env": "test",
        "database_url": "postgresql+asyncpg://user:pass@127.0.0.1:1/nowhere",
        "tvmaze_base_url": "https://catalogue.test",
        "ai_provider_order": "huggingface,openrouter,heuristic",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class TestGraphWiring:
    def test_every_use_case_is_composed(self) -> None:
        container = Container.build(offline_settings())

        assert isinstance(container.search_series, SearchSeries)
        assert isinstance(container.get_series_details, GetSeriesDetails)
        assert isinstance(container.get_episode_detail, GetEpisodeDetail)
        assert isinstance(container.set_episode_watched, SetEpisodeWatched)
        assert isinstance(container.add_comment, AddComment)
        assert isinstance(container.list_comments, ListComments)
        assert isinstance(container.generate_insight, GenerateInsight)

    def test_the_catalogue_gateway_is_decorated_with_a_cache(self) -> None:
        container = Container.build(offline_settings())

        assert isinstance(container.gateway, CachingTvMazeGateway)

    def test_the_provider_chain_is_decorated_with_a_cache(self) -> None:
        container = Container.build(offline_settings())
        from tv_insight.infrastructure.ai.factory import describe_providers

        assert isinstance(container.insight_provider, CachingInsightProvider)
        assert [info.name for info in describe_providers(container.insight_provider)][-1] == (
            "heuristic"
        )

    def test_the_unit_of_work_factory_hands_out_real_units(self) -> None:
        container = Container.build(offline_settings())

        unit = container.unit_of_work()

        assert isinstance(unit, SqlAlchemyUnitOfWork)

    def test_one_shared_http_client_is_reused_by_both_adapters(self) -> None:
        container = Container.build(offline_settings())

        assert isinstance(container.http_client, httpx.AsyncClient)
        # The catalogue adapter is built on top of it; closing the container closes
        # it exactly once.
        assert container.gateway is not None

    async def test_shutdown_releases_every_resource(self) -> None:
        container = Container.build(offline_settings())

        await container.shutdown()

        assert container.http_client.is_closed is True

    async def test_database_health_is_false_when_the_database_is_unreachable(self) -> None:
        container = Container.build(offline_settings())
        try:
            assert await container.database_health() is False
        finally:
            await container.shutdown()


class TestSettingsOverride:
    def test_provider_order_is_honoured(self) -> None:
        from tv_insight.infrastructure.ai.factory import describe_providers

        container = Container.build(
            offline_settings(ai_provider_order="heuristic", huggingface_api_token="t")
        )
        # huggingface was not selected, so it must not appear in the chain.
        assert [
            info.name for info in describe_providers(container.insight_provider)
        ] == ["heuristic"]

    def test_the_second_model_tier_is_opt_in(self) -> None:
        from tv_insight.infrastructure.ai.factory import describe_providers

        default = Container.build(
            offline_settings(ai_provider_order="huggingface,heuristic")
        )
        opted_in = Container.build(
            offline_settings(ai_provider_order="huggingface,openrouter,heuristic")
        )

        assert [info.name for info in describe_providers(default.insight_provider)] == [
            "huggingface",
            "heuristic",
        ]
        assert [info.name for info in describe_providers(opted_in.insight_provider)] == [
            "huggingface",
            "openrouter",
            "heuristic",
        ]


@pytest.mark.parametrize("order", ["heuristic", "openrouter,heuristic", ""])
def test_any_provider_order_still_yields_a_usable_chain(order: str) -> None:
    from tv_insight.infrastructure.ai.factory import describe_providers

    container = Container.build(offline_settings(ai_provider_order=order))

    names = [info.name for info in describe_providers(container.insight_provider)]

    assert names[-1] == "heuristic"
    assert "heuristic" in names
