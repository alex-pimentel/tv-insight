"""Level 3: the caching decorator around the catalogue gateway."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pytest

from tests.fakes import InMemoryTvMazeGateway
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.entities.series import Series
from tv_insight.domain.value_objects import SearchTerm, SeriesId
from tv_insight.infrastructure.cache import AsyncTtlCache
from tv_insight.infrastructure.tvmaze.caching import CachingTvMazeGateway


class CountingGateway(InMemoryTvMazeGateway):
    """Counts how many times the underlying gateway was actually hit."""

    def __init__(
        self,
        series: Sequence[Series] = (),
        episodes: Mapping[int, Sequence[Episode]] | None = None,
    ) -> None:
        super().__init__(series=series, episodes=episodes)
        self.series_calls = 0

    async def get_series(self, series_id: SeriesId) -> Series:
        self.series_calls += 1
        return await super().get_series(series_id)


@pytest.fixture
def counting(
    breaking_bad: Series, other_series: Series, episodes: Sequence[Episode]
) -> CountingGateway:
    return CountingGateway(
        series=(breaking_bad, other_series), episodes={1: episodes}
    )


@pytest.fixture
def caching_gateway(counting: CountingGateway) -> CachingTvMazeGateway:
    return CachingTvMazeGateway(counting, AsyncTtlCache(60))


async def test_search_is_cached_case_insensitively(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    await caching_gateway.search(SearchTerm("breaking"))
    await caching_gateway.search(SearchTerm("BREAKING"))

    assert counting.search_calls == ["breaking"]


async def test_series_lookup_is_cached(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    first = await caching_gateway.get_series(SeriesId(1))
    second = await caching_gateway.get_series(SeriesId(1))

    assert counting.series_calls == 1
    assert first is second


async def test_episodes_are_cached_per_series(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    first = await caching_gateway.get_episodes(SeriesId(1))
    second = await caching_gateway.get_episodes(SeriesId(1))

    assert isinstance(first, EpisodeGuide)
    assert first is second
    assert first.total_episodes == 4
    assert counting.episode_calls == [1]


async def test_different_series_are_cached_separately(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    await caching_gateway.get_episodes(SeriesId(1))
    other = await caching_gateway.get_episodes(SeriesId(2))

    assert other.total_episodes == 0
    assert counting.episode_calls == [1, 2]


async def test_close_is_forwarded(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    await caching_gateway.aclose()

    assert counting.closed is True


async def test_the_three_operations_do_not_collide(
    caching_gateway: CachingTvMazeGateway, counting: CountingGateway
) -> None:
    await caching_gateway.get_series(SeriesId(1))
    await caching_gateway.get_episodes(SeriesId(1))

    assert counting.series_calls == 1
    assert counting.episode_calls == [1]
