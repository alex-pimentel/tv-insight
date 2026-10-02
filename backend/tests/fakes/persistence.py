"""In-memory persistence.

The repositories mimic the SQL implementation, including newest-first ordering
and the idempotent semantics of the watched flag.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Self

from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.ports.repositories import (
    CommentRepository,
    InsightRepository,
    WatchedEpisodeRepository,
)
from tv_insight.domain.value_objects import (
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)


class InMemoryCommentRepository(CommentRepository):
    def __init__(self) -> None:
        self.rows: list[Comment] = []

    async def add(self, comment: Comment) -> Comment:
        self.rows.append(comment)
        return comment

    async def list_for_series(
        self, series_id: SeriesId, limit: int | None = None
    ) -> Sequence[Comment]:
        matches = [
            row
            for row in self._newest_first()
            if row.series_id == series_id and row.target is ContentTarget.SERIES
        ]
        return matches[:limit] if limit is not None else matches

    async def list_for_episode(
        self, episode_id: EpisodeId, limit: int | None = None
    ) -> Sequence[Comment]:
        matches = [
            row
            for row in self._newest_first()
            if row.episode_id == episode_id and row.target is ContentTarget.EPISODE
        ]
        return matches[:limit] if limit is not None else matches

    async def count_for_series(self, series_id: SeriesId) -> int:
        return sum(
            1
            for row in self.rows
            if row.series_id == series_id and row.target is ContentTarget.SERIES
        )

    async def count_for_episode(self, episode_id: EpisodeId) -> int:
        return sum(1 for row in self.rows if row.episode_id == episode_id)

    def _newest_first(self) -> list[Comment]:
        return sorted(self.rows, key=lambda row: row.created_at, reverse=True)


class InMemoryWatchedEpisodeRepository(WatchedEpisodeRepository):
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], WatchedEpisode] = {}

    async def save(self, watched: WatchedEpisode) -> None:
        self.rows[(watched.viewer_id.value, watched.episode_id.value)] = watched

    async def remove(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None:
        self.rows.pop((viewer_id.value, episode_id.value), None)

    async def exists(self, viewer_id: ViewerId, episode_id: EpisodeId) -> bool:
        return (viewer_id.value, episode_id.value) in self.rows

    async def list_episode_ids(
        self, viewer_id: ViewerId, series_id: SeriesId
    ) -> frozenset[EpisodeId]:
        return frozenset(
            EpisodeId(episode)
            for (viewer, episode), row in self.rows.items()
            if viewer == viewer_id.value and row.series_id == series_id
        )


class InMemoryInsightRepository(InsightRepository):
    """The stored insights, keyed by subject — exactly like the SQL table."""

    def __init__(self) -> None:
        self.rows: dict[tuple[ContentTarget, int], StoredInsight] = {}

    async def get(self, target: ContentTarget, target_id: int) -> StoredInsight | None:
        return self.rows.get((target, target_id))

    async def save(self, insight: StoredInsight) -> StoredInsight:
        self.rows[(insight.target, insight.target_id)] = insight
        return insight


class InMemoryUnitOfWork(UnitOfWork):
    """Shares one set of in-memory tables across every context manager."""

    def __init__(self, comments: InMemoryCommentRepository | None = None) -> None:
        self.comments = comments or InMemoryCommentRepository()
        self.watches = InMemoryWatchedEpisodeRepository()
        self.insights = InMemoryInsightRepository()
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollbacks += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    def factory(self) -> InMemoryUnitOfWork:
        """Return a callable usable as the ``unit_of_work`` port."""
        return self
