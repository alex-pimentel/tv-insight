"""Use case: add a comment to a series or to an episode."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from tv_insight.application.dto import CommentView
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import comment_to_view
from tv_insight.application.ports.clock import Clock
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)


class AddComment:
    """Validates the target, then persists the comment."""

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        clock: Clock,
        new_id: Callable[[], str] = lambda: uuid4().hex,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._clock = clock
        self._new_id = new_id

    async def execute(
        self,
        *,
        series_id: int,
        viewer_id: str,
        text: str,
        episode_id: int | None = None,
    ) -> CommentView:
        with translated_domain_errors():
            series_identifier = SeriesId(series_id)
            viewer = ViewerId(viewer_id)
            body = CommentText(text)

        # Existence checks: a comment can only hang off something the catalogue
        # actually knows, so the table never accumulates orphans.
        await self._gateway.get_series(series_identifier)

        episode_identifier: EpisodeId | None = None
        episode_codes: dict[EpisodeId, str] | None = None
        if episode_id is not None:
            with translated_domain_errors():
                episode_identifier = EpisodeId(episode_id)
            guide = await self._gateway.get_episodes(series_identifier)
            with translated_domain_errors():
                episode = guide.find(episode_identifier)
            episode_codes = {episode.id: episode.code}

        comment = Comment(
            id=self._new_id(),
            viewer_id=viewer,
            target=ContentTarget.EPISODE if episode_identifier else ContentTarget.SERIES,
            series_id=series_identifier,
            episode_id=episode_identifier,
            text=body,
            created_at=self._clock.now(),
        )

        async with self._uow_factory() as uow:
            stored = await uow.comments.add(comment)
            await uow.commit()

        return comment_to_view(stored, viewer_id=viewer, episode_codes=episode_codes)
