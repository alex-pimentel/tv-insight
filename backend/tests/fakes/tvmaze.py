"""In-memory catalogue gateway."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from tv_insight.application.errors import ResourceNotFound
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.entities.series import Series
from tv_insight.domain.value_objects import SearchTerm, SeriesId


class InMemoryTvMazeGateway(TvMazeGateway):
    """Serves series and episodes from plain dictionaries."""

    def __init__(
        self,
        series: Sequence[Series] = (),
        episodes: Mapping[int, Sequence[Episode]] | None = None,
    ) -> None:
        self.series: list[Series] = list(series)
        self.episodes: dict[int, list[Episode]] = {
            key: list(value) for key, value in (episodes or {}).items()
        }
        self.search_calls: list[str] = []
        self.episode_calls: list[int] = []
        self.closed = False

    async def search(self, term: SearchTerm) -> Sequence[Series]:
        self.search_calls.append(str(term))
        needle = str(term).lower()
        return tuple(series for series in self.series if needle in series.name.lower())

    async def get_series(self, series_id: SeriesId) -> Series:
        for series in self.series:
            if series.id == series_id:
                return series
        raise ResourceNotFound(f"Unknown series {series_id}")

    async def get_episodes(self, series_id: SeriesId) -> EpisodeGuide:
        self.episode_calls.append(series_id.value)
        if series_id.value not in self.episodes and not any(
            series.id == series_id for series in self.series
        ):
            raise ResourceNotFound(f"Unknown series {series_id}")
        return EpisodeGuide.from_episodes(
            series_id, list(self.episodes.get(series_id.value, ()))
        )

    async def aclose(self) -> None:
        self.closed = True
