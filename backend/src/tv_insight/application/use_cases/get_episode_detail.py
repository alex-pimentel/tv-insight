"""Use case: the episode detail screen (summary, comments, next episode)."""

from __future__ import annotations

from collections.abc import Callable

from tv_insight.application.dto import EpisodeDetail
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import comment_to_view, episode_to_view, series_to_card
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId

COMMENT_PREVIEW_LIMIT = 50


class GetEpisodeDetail:
    """Series header + one episode + its comments + the following episode."""

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        comment_preview_limit: int = COMMENT_PREVIEW_LIMIT,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._comment_preview_limit = comment_preview_limit

    async def execute(self, series_id: int, episode_id: int, viewer_id: str) -> EpisodeDetail:
        with translated_domain_errors():
            series_identifier = SeriesId(series_id)
            episode_identifier = EpisodeId(episode_id)
            viewer = ViewerId(viewer_id)

        series = await self._gateway.get_series(series_identifier)
        guide = await self._gateway.get_episodes(series_identifier)
        with translated_domain_errors():
            episode = guide.find(episode_identifier)

        async with self._uow_factory() as uow:
            watched = await uow.watches.exists(viewer, episode_identifier)
            comments = await uow.comments.list_for_episode(
                episode_identifier, limit=self._comment_preview_limit
            )
            comment_count = await uow.comments.count_for_episode(episode_identifier)

        following = self._next_episode(guide.episodes, episode)
        codes = {item.id: item.code for item in guide.episodes}

        return EpisodeDetail(
            series=series_to_card(series),
            episode=episode_to_view(episode, watched=watched),
            comment_count=comment_count,
            comments=tuple(
                comment_to_view(comment, viewer_id=viewer, episode_codes=codes)
                for comment in comments
            ),
            next_episode=episode_to_view(following, watched=False) if following else None,
        )

    @staticmethod
    def _next_episode(episodes: tuple[Episode, ...], current: Episode) -> Episode | None:
        ordered = sorted(episodes, key=Episode.sort_key)
        for index, episode in enumerate(ordered):
            if episode.id == current.id:
                return ordered[index + 1] if index + 1 < len(ordered) else None
        return None
