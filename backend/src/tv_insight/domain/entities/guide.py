"""Episode grouping.

``EpisodeGuide`` is the aggregate the UI consumes: episodes grouped by season,
plus the queries the use cases need. All of it is pure logic and therefore the
easiest thing in the codebase to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass

from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.exceptions import NotFound
from tv_insight.domain.value_objects import EpisodeId, SeasonNumber, SeriesId


@dataclass(frozen=True, slots=True)
class Season:
    """A season and the episodes that belong to it, already ordered."""

    number: SeasonNumber
    episodes: tuple[Episode, ...]

    @property
    def episode_count(self) -> int:
        return len(self.episodes)

    @property
    def label(self) -> str:
        return "Specials" if self.number.is_specials else f"Season {self.number.value}"

    def contains(self, episode_id: EpisodeId) -> bool:
        return any(episode.id == episode_id for episode in self.episodes)


@dataclass(frozen=True, slots=True)
class EpisodeGuide:
    """Every episode of one series, with season grouping."""

    series_id: SeriesId
    episodes: tuple[Episode, ...] = ()

    @classmethod
    def from_episodes(cls, series_id: SeriesId, episodes: list[Episode]) -> EpisodeGuide:
        return cls(series_id=series_id, episodes=tuple(episodes))

    @property
    def total_episodes(self) -> int:
        return len(self.episodes)

    def seasons(self) -> tuple[Season, ...]:
        """Group by season, specials (season 0) last, episodes ordered."""
        grouped: dict[int, list[Episode]] = {}
        for episode in self.episodes:
            grouped.setdefault(episode.season.value, []).append(episode)

        ordered_numbers = sorted(grouped, key=lambda number: (number == 0, number))
        return tuple(
            Season(
                number=SeasonNumber(number),
                episodes=tuple(sorted(grouped[number], key=Episode.sort_key)),
            )
            for number in ordered_numbers
        )

    def find(self, episode_id: EpisodeId) -> Episode:
        for episode in self.episodes:
            if episode.id == episode_id:
                return episode
        raise NotFound(f"Episode {episode_id} does not belong to series {self.series_id}")
