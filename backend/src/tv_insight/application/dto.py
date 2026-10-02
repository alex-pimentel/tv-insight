"""Data transfer objects returned by the use cases.

Plain dataclasses, deliberately *not* the domain entities: the presentation layer
gets a shape that is stable and JSON friendly, while the entities stay free to
evolve. Presentation maps these to its own response models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class SeriesCard:
    """Compact representation used in search results and detail headers."""

    id: int
    name: str
    year: int | None = None
    poster_url: str | None = None
    poster_thumbnail_url: str | None = None
    genres: tuple[str, ...] = ()
    status: str | None = None
    rating: float | None = None
    network: str | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class EpisodeView:
    id: int
    name: str
    season: int
    number: int
    code: str
    summary: str
    airdate: date | None = None
    runtime_minutes: int | None = None
    image_url: str | None = None
    watched: bool = False


@dataclass(frozen=True, slots=True)
class SeasonView:
    number: int
    label: str
    episodes: tuple[EpisodeView, ...] = ()
    watched: int = 0
    total: int = 0

    @property
    def progress(self) -> float:
        return self.watched / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class CommentView:
    id: str
    target: str
    series_id: int
    text: str
    created_at: datetime
    episode_id: int | None = None
    episode_code: str | None = None
    author: str = "Anonymous viewer"
    mine: bool = False


@dataclass(frozen=True, slots=True)
class SeriesDetail:
    """Everything the detail screen needs, in a single response."""

    series: SeriesCard
    summary: str
    seasons: tuple[SeasonView, ...] = ()
    watched: int = 0
    total_episodes: int = 0
    progress: float = 0.0
    comment_count: int = 0
    comments: tuple[CommentView, ...] = ()


@dataclass(frozen=True, slots=True)
class EpisodeDetail:
    series: SeriesCard
    episode: EpisodeView
    comment_count: int = 0
    comments: tuple[CommentView, ...] = ()
    next_episode: EpisodeView | None = None


@dataclass(frozen=True, slots=True)
class InsightView:
    """The AI answer, plus provenance so the UI can be honest about fallbacks.

    ``cached`` means the answer was served from the durable store without calling
    a provider. ``based_on_comment_count`` is the number of comments the insight
    was built from - the client asked to regenerate as soon as a new comment
    arrives, so this is shown for traceability.
    """

    text: str
    provider: str
    degraded: bool = False
    cached: bool = False
    generated_at: datetime | None = None
    target: str = "series"
    target_id: int = 0
    based_on_comment_count: int = 0
    notes: tuple[str, ...] = field(default_factory=tuple)
