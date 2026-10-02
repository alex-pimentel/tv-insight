"""Use case: mark or unmark an episode as watched."""

from __future__ import annotations

from collections.abc import Callable

from tv_insight.application.dto import EpisodeView
from tv_insight.application.errors import translated_domain_errors
from tv_insight.application.mappers import episode_to_view
from tv_insight.application.ports.clock import Clock
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId


class SetEpisodeWatched:
    """Idempotent toggle.

    The episode is first located inside the series guide, which guarantees a
    "watched" row can never point at an episode of another series. The guide
    lookup is served from the gateway cache, so this costs nothing on repeat.
    """

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        clock: Clock,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._clock = clock

    async def execute(
        self,
        series_id: int,
        episode_id: int,
        viewer_id: str,
        *,
        watched: bool,
    ) -> EpisodeView:
        with translated_domain_errors():
            series_identifier = SeriesId(series_id)
            episode_identifier = EpisodeId(episode_id)
            viewer = ViewerId(viewer_id)

        guide = await self._gateway.get_episodes(series_identifier)
        with translated_domain_errors():
            episode = guide.find(episode_identifier)

        async with self._uow_factory() as uow:
            if watched:
                await uow.watches.save(
                    WatchedEpisode(
                        viewer_id=viewer,
                        series_id=series_identifier,
                        episode_id=episode_identifier,
                        watched_at=self._clock.now(),
                    )
                )
            else:
                await uow.watches.remove(viewer, episode_identifier)
            await uow.commit()

        return episode_to_view(episode, watched=watched)
