"""The ``Series`` entity: everything the module knows about a TV show."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.text import to_plain_text
from tv_insight.domain.value_objects import Genre, Rating, SeriesId

RUNNING_STATUSES = frozenset({"running", "in development", "to be determined"})


@dataclass(frozen=True, slots=True)
class Series:
    """An immutable snapshot of a series as published by the catalogue."""

    id: SeriesId
    name: str
    summary: str | None = None
    genres: tuple[Genre, ...] = field(default_factory=tuple)
    premiered: date | None = None
    ended: date | None = None
    status: str | None = None
    poster_url: str | None = None
    poster_thumbnail_url: str | None = None
    network: str | None = None
    rating: Rating | None = None
    language: str | None = None
    official_url: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidValue("Series name must not be empty")

    @property
    def year(self) -> int | None:
        """Year shown next to the title in search results."""
        reference = self.premiered or self.ended
        return reference.year if reference else None

    @property
    def is_running(self) -> bool:
        if not self.status:
            return False
        return self.status.strip().lower() in RUNNING_STATUSES

    @property
    def genre_names(self) -> tuple[str, ...]:
        return tuple(genre.value for genre in self.genres)

    def synopsis(self, fallback: str = "No summary available for this series.") -> str:
        """Summary with HTML stripped and a sensible fallback."""
        return to_plain_text(self.summary) or fallback
