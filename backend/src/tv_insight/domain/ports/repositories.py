"""Repository ports owned by the domain.

These are the *contracts* the inner layers need; the SQL implementation lives in
``infrastructure``. Declaring them here is what lets the dependency rule point
inwards: infrastructure depends on the domain, never the other way around.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.value_objects import (
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)


class WatchedEpisodeRepository(ABC):
    """Per-viewer persistence of the "seen" flag."""

    @abstractmethod
    async def save(self, watched: WatchedEpisode) -> None:
        """Idempotently record that the episode was watched."""

    @abstractmethod
    async def remove(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None:
        """Idempotently clear the watched flag."""

    @abstractmethod
    async def exists(self, viewer_id: ViewerId, episode_id: EpisodeId) -> bool:
        """Whether the viewer already watched the episode."""

    @abstractmethod
    async def list_episode_ids(
        self, viewer_id: ViewerId, series_id: SeriesId
    ) -> frozenset[EpisodeId]:
        """Every watched episode of one series for one viewer."""


class CommentRepository(ABC):
    """Persistence of series and episode comments."""

    @abstractmethod
    async def add(self, comment: Comment) -> Comment:
        """Store a new comment and return it."""

    @abstractmethod
    async def list_for_series(
        self, series_id: SeriesId, limit: int | None = None
    ) -> Sequence[Comment]:
        """Series level comments, newest first."""

    @abstractmethod
    async def list_for_episode(
        self, episode_id: EpisodeId, limit: int | None = None
    ) -> Sequence[Comment]:
        """Comments of one episode, newest first."""

    @abstractmethod
    async def count_for_series(self, series_id: SeriesId) -> int:
        """Series level comment count, used for the insight input."""

    @abstractmethod
    async def count_for_episode(self, episode_id: EpisodeId) -> int:
        """Episode comment count, used for the insight input."""


class InsightRepository(ABC):
    """Persistence of generated insights.

    One row per (target, target_id). The stored row is both the cache and the
    record of what the insight was based on.
    """

    @abstractmethod
    async def get(self, target: ContentTarget, target_id: int) -> StoredInsight | None:
        """Return the stored insight for a subject, or ``None``."""

    @abstractmethod
    async def save(self, insight: StoredInsight) -> StoredInsight:
        """Insert or replace the insight for its subject."""
