"""Value objects: immutable, self-validating, no identity.

Grouped in a single module on purpose: they share one cohesive responsibility
(guarding the primitives that flow through the system) and are small enough to
read at a glance.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from tv_insight.domain.exceptions import InvalidValue

MAX_COMMENT_LENGTH = 2000


class ContentTarget(StrEnum):
    """What a piece of user generated content is attached to.

    Shared by the ``Comment`` and ``StoredInsight`` aggregates: both are "about a
    series" or "about an episode". Promoted to a value object rather than
    duplicated, so the two cannot drift apart.
    """

    SERIES = "series"
    EPISODE = "episode"


@dataclass(frozen=True, slots=True)
class SeriesId:
    """Identity of a TV series. Mirrors the TVMaze numeric identifier."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value <= 0:
            raise InvalidValue(f"SeriesId must be a positive integer, got {self.value!r}")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class EpisodeId:
    """Identity of a single episode, unique across every series."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value <= 0:
            raise InvalidValue(f"EpisodeId must be a positive integer, got {self.value!r}")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ViewerId:
    """Opaque identity of the person browsing the app.

    The assignment has no authentication, so a signed cookie carries a random
    identifier. That is enough to make "watched" state and comments persist per
    visitor across reloads without inventing an account system.
    """

    value: str

    MAX_LENGTH = 64

    def __post_init__(self) -> None:
        cleaned = self.value.strip()
        if not cleaned:
            raise InvalidValue("ViewerId must not be empty")
        if len(cleaned) > self.MAX_LENGTH:
            raise InvalidValue(f"ViewerId must be at most {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SeasonNumber:
    """Season index as published by TVMaze. Season 0 holds the specials."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0:
            raise InvalidValue(f"SeasonNumber must be zero or positive, got {self.value!r}")

    @property
    def is_specials(self) -> bool:
        return self.value == 0

    def __str__(self) -> str:
        return "Specials" if self.is_specials else f"Season {self.value}"


@dataclass(frozen=True, slots=True)
class EpisodeNumber:
    """Position of an episode inside its season."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0:
            raise InvalidValue(f"EpisodeNumber must be zero or positive, got {self.value!r}")

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class Rating:
    """TVMaze average rating in the 0..10 range."""

    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.value) <= 10.0:
            raise InvalidValue(f"Rating must be between 0 and 10, got {self.value!r}")

    def __float__(self) -> float:
        return float(self.value)


@dataclass(frozen=True, slots=True)
class Genre:
    """A normalised genre label ("Drama", "Science-Fiction", ...)."""

    value: str

    MAX_LENGTH = 60

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())
        if not cleaned:
            raise InvalidValue("Genre must not be empty")
        if len(cleaned) > self.MAX_LENGTH:
            raise InvalidValue(f"Genre must be at most {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CommentText:
    """The body of a comment. Normalised and length bounded."""

    value: str

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())
        if not cleaned:
            raise InvalidValue("Comment text must not be empty")
        if len(cleaned) > MAX_COMMENT_LENGTH:
            raise InvalidValue(f"Comment text must be at most {MAX_COMMENT_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SearchTerm:
    """A user supplied query for the series catalogue."""

    value: str

    MIN_LENGTH = 2
    MAX_LENGTH = 100

    def __post_init__(self) -> None:
        cleaned = " ".join(self.value.split())
        if len(cleaned) < self.MIN_LENGTH:
            raise InvalidValue(f"Search term must have at least {self.MIN_LENGTH} characters")
        if len(cleaned) > self.MAX_LENGTH:
            raise InvalidValue(f"Search term must be at most {self.MAX_LENGTH} characters")
        object.__setattr__(self, "value", cleaned)

    def __str__(self) -> str:
        return self.value
