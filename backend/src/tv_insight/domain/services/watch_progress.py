"""Watch progress calculations.

Pure arithmetic over the ``EpisodeGuide`` aggregate: the UI needs per season
progress bars and an overall completion ratio, and both are easy to test because
nothing here touches a database or the network.
"""

from __future__ import annotations

from dataclasses import dataclass

from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.value_objects import EpisodeId, SeasonNumber


@dataclass(frozen=True, slots=True)
class SeasonProgress:
    """How much of one season the viewer has already seen."""

    number: SeasonNumber
    label: str
    watched: int
    total: int

    @property
    def ratio(self) -> float:
        return self.watched / self.total if self.total else 0.0

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.watched == self.total

    @property
    def is_started(self) -> bool:
        return self.watched > 0


@dataclass(frozen=True, slots=True)
class WatchSummary:
    """Overall progress plus the per season breakdown."""

    watched: int
    total: int
    seasons: tuple[SeasonProgress, ...]

    @property
    def ratio(self) -> float:
        return self.watched / self.total if self.total else 0.0

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.watched == self.total


class WatchProgressService:
    """Computes watch progress from a guide and a set of watched episodes."""

    def summarize(
        self, guide: EpisodeGuide, watched: frozenset[EpisodeId]
    ) -> WatchSummary:
        relevant = {episode.id for episode in guide.episodes}
        watched_ids = watched & relevant

        seasons = tuple(
            SeasonProgress(
                number=season.number,
                label=season.label,
                watched=sum(1 for episode in season.episodes if episode.id in watched_ids),
                total=season.episode_count,
            )
            for season in guide.seasons()
        )

        return WatchSummary(
            watched=len(watched_ids),
            total=guide.total_episodes,
            seasons=seasons,
        )
