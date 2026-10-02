"""Use case: search the catalogue for TV series."""

from __future__ import annotations

from collections.abc import Sequence

from tv_insight.application.dto import SeriesCard
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import series_to_card
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.value_objects import SearchTerm

DEFAULT_LIMIT = 24


class SearchSeries:
    """``GET /search/shows?q=`` mapped to a list of compact cards."""

    def __init__(self, gateway: TvMazeGateway, limit: int = DEFAULT_LIMIT) -> None:
        self._gateway = gateway
        self._limit = limit

    async def execute(self, query: str) -> Sequence[SeriesCard]:
        with translated_domain_errors():
            term = SearchTerm(query)

        series = await self._gateway.search(term)
        return tuple(series_to_card(item) for item in series[: self._limit])
