"""The ``Episode`` entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from tv_insight.domain.text import to_plain_text
from tv_insight.domain.value_objects import (
    EpisodeId,
    EpisodeNumber,
    SeasonNumber,
    SeriesId,
)


@dataclass(frozen=True, slots=True)
class Episode:
    """One episode of a series. Immutable snapshot from the catalogue."""

    id: EpisodeId
    series_id: SeriesId
    name: str
    season: SeasonNumber
    number: EpisodeNumber
    summary: str | None = None
    airdate: date | None = None
    runtime_minutes: int | None = None
    image_url: str | None = None

    def synopsis(self, fallback: str = "No summary available for this episode.") -> str:
        return to_plain_text(self.summary) or fallback

    @property
    def code(self) -> str:
        """Human readable coordinate such as ``S02E07``."""
        return f"S{self.season.value:02d}E{self.number.value:02d}"

    @property
    def is_special(self) -> bool:
        return self.season.is_specials

    def sort_key(self) -> tuple[int, int]:
        """Ordering used inside a season listing."""
        return (self.season.value, self.number.value)
