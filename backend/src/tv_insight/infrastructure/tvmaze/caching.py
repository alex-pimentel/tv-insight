"""Decorator that adds an in-process TTL cache to any ``TvMazeGateway``.

Composable on purpose: the HTTP adapter stays unaware of caching and the caching
layer stays unaware of HTTP, which is exactly what the Decorator pattern buys us.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.entities.series import Series
from tv_insight.domain.value_objects import SearchTerm, SeriesId
from tv_insight.infrastructure.cache import AsyncTtlCache

CacheKey = tuple[str, object]


class CachingTvMazeGateway(TvMazeGateway):
    """Serves repeated catalogue reads from memory within the configured TTL."""

    def __init__(
        self,
        inner: TvMazeGateway,
        cache: AsyncTtlCache[CacheKey, Any],
    ) -> None:
        self._inner = inner
        self._cache = cache

    async def search(self, term: SearchTerm) -> Sequence[Series]:
        value, _ = await self._cache.get_or_create(
            ("search", str(term).lower()), lambda: self._inner.search(term)
        )
        return cast("Sequence[Series]", value)

    async def get_series(self, series_id: SeriesId) -> Series:
        value, _ = await self._cache.get_or_create(
            ("series", series_id.value), lambda: self._inner.get_series(series_id)
        )
        return cast("Series", value)

    async def get_episodes(self, series_id: SeriesId) -> EpisodeGuide:
        value, _ = await self._cache.get_or_create(
            ("episodes", series_id.value), lambda: self._inner.get_episodes(series_id)
        )
        return cast("EpisodeGuide", value)

    async def aclose(self) -> None:
        await self._inner.aclose()
