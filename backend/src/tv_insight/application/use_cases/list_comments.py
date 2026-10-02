"""Use case: list the comments of a series or of one episode."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from tv_insight.application.dto import CommentView
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import comment_to_view
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId

DEFAULT_LIMIT = 100


class ListComments:
    """Series comments and episode comments share one use case.

    The domain models them as a single ``Comment`` aggregate with a target, so a
    single query surface is the faithful representation.
    """

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        limit: int = DEFAULT_LIMIT,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._limit = limit

    async def execute(
        self,
        *,
        series_id: int,
        viewer_id: str,
        episode_id: int | None = None,
    ) -> Sequence[CommentView]:
        with translated_domain_errors():
            series_identifier = SeriesId(series_id)
            viewer = ViewerId(viewer_id)
            episode_identifier = EpisodeId(episode_id) if episode_id is not None else None

        episode_codes: dict[EpisodeId, str] = {}
        if episode_identifier is not None:
            guide = await self._gateway.get_episodes(series_identifier)
            episode_codes = {episode.id: episode.code for episode in guide.episodes}

        async with self._uow_factory() as uow:
            comments = (
                await uow.comments.list_for_episode(episode_identifier, limit=self._limit)
                if episode_identifier is not None
                else await uow.comments.list_for_series(series_identifier, limit=self._limit)
            )

        return tuple(
            comment_to_view(comment, viewer_id=viewer, episode_codes=episode_codes)
            for comment in comments
        )
