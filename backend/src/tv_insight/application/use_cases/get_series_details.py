"""Use case: everything shown on the series detail screen."""

from __future__ import annotations

from collections.abc import Callable

from tv_insight.application.dto import SeasonView, SeriesDetail
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import comment_to_view, episode_to_view, series_to_card
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.services.watch_progress import (
    WatchProgressService,
    WatchSummary,
)
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId

COMMENT_PREVIEW_LIMIT = 20


class GetSeriesDetails:
    """Series metadata + episode guide + progress + comments in one response.

    Aggregating server side is a conscious trade-off: the UI does one round trip
    instead of four, at the cost of the use case knowing about all of it.
    """

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        progress_service: WatchProgressService,
        comment_preview_limit: int = COMMENT_PREVIEW_LIMIT,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._progress = progress_service
        self._comment_preview_limit = comment_preview_limit

    async def execute(self, series_id: int, viewer_id: str) -> SeriesDetail:
        with translated_domain_errors():
            identifier = SeriesId(series_id)
            viewer = ViewerId(viewer_id)

        series = await self._gateway.get_series(identifier)
        guide = await self._gateway.get_episodes(identifier)

        async with self._uow_factory() as uow:
            watched = await uow.watches.list_episode_ids(viewer, identifier)
            comments = await uow.comments.list_for_series(
                identifier, limit=self._comment_preview_limit
            )
            comment_count = await uow.comments.count_for_series(identifier)

        summary = self._progress.summarize(guide, watched)
        episode_codes = {episode.id: episode.code for episode in guide.episodes}

        return SeriesDetail(
            series=series_to_card(series),
            summary=series.synopsis(),
            seasons=self._seasons(guide, summary, watched),
            watched=summary.watched,
            total_episodes=summary.total,
            progress=summary.ratio,
            comment_count=comment_count,
            comments=tuple(
                comment_to_view(comment, viewer_id=viewer, episode_codes=episode_codes)
                for comment in comments
            ),
        )

    @staticmethod
    def _seasons(
        guide: EpisodeGuide,
        summary: WatchSummary,
        watched: frozenset[EpisodeId],
    ) -> tuple[SeasonView, ...]:
        progress_by_number = {season.number.value: season for season in summary.seasons}
        views: list[SeasonView] = []
        for season in guide.seasons():
            progress = progress_by_number[season.number.value]
            views.append(
                SeasonView(
                    number=season.number.value,
                    label=season.label,
                    episodes=tuple(
                        episode_to_view(episode, watched=episode.id in watched)
                        for episode in season.episodes
                    ),
                    watched=progress.watched,
                    total=progress.total,
                )
            )
        return tuple(views)
