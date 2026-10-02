"""The ``WatchedEpisode`` entity: a viewer ticked an episode as seen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId


@dataclass(frozen=True, slots=True)
class WatchedEpisode:
    """Fact that ``viewer`` watched ``episode`` at ``watched_at``.

    The pair (viewer, episode) is the natural key: marking twice is idempotent
    and unmarking removes the row.
    """

    viewer_id: ViewerId
    series_id: SeriesId
    episode_id: EpisodeId
    watched_at: datetime

    def __post_init__(self) -> None:
        if self.watched_at.tzinfo is None:
            raise InvalidValue("WatchedEpisode.watched_at must be timezone aware")
