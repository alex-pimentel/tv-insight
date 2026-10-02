"""Repository implementations backed by SQLAlchemy.

Each method is a query plus a translation into domain objects. No business rule
lives here: if you find an ``if`` that is not about persistence, it belongs in the
domain.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.ports.repositories import (
    CommentRepository,
    InsightRepository,
    WatchedEpisodeRepository,
)
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)
from tv_insight.infrastructure.db.models import (
    CommentRow,
    InsightRow,
    WatchedEpisodeRow,
)


def _to_comment(row: CommentRow) -> Comment:
    return Comment(
        id=row.id,
        viewer_id=ViewerId(row.viewer_id),
        target=ContentTarget(row.target),
        series_id=SeriesId(row.series_id),
        episode_id=EpisodeId(row.episode_id) if row.episode_id is not None else None,
        text=CommentText(row.text),
        created_at=row.created_at,
    )


class SqlCommentRepository(CommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, comment: Comment) -> Comment:
        self._session.add(
            CommentRow(
                id=comment.id,
                viewer_id=comment.viewer_id.value,
                target=comment.target.value,
                series_id=comment.series_id.value,
                episode_id=comment.episode_id.value if comment.episode_id else None,
                text=comment.text.value,
                created_at=comment.created_at,
            )
        )
        await self._session.flush()
        return comment

    async def list_for_series(
        self, series_id: SeriesId, limit: int | None = None
    ) -> Sequence[Comment]:
        statement = (
            select(CommentRow)
            .where(
                CommentRow.series_id == series_id.value,
                CommentRow.target == ContentTarget.SERIES.value,
            )
            .order_by(CommentRow.created_at.desc(), CommentRow.id.desc())
        )
        return await self._fetch(statement, limit)

    async def list_for_episode(
        self, episode_id: EpisodeId, limit: int | None = None
    ) -> Sequence[Comment]:
        statement = (
            select(CommentRow)
            .where(
                CommentRow.episode_id == episode_id.value,
                CommentRow.target == ContentTarget.EPISODE.value,
            )
            .order_by(CommentRow.created_at.desc(), CommentRow.id.desc())
        )
        return await self._fetch(statement, limit)

    async def count_for_series(self, series_id: SeriesId) -> int:
        return await self._count(
            CommentRow.series_id == series_id.value,
            CommentRow.target == ContentTarget.SERIES.value,
        )

    async def count_for_episode(self, episode_id: EpisodeId) -> int:
        return await self._count(
            CommentRow.episode_id == episode_id.value,
            CommentRow.target == ContentTarget.EPISODE.value,
        )

    async def _fetch(
        self, statement: Select[Any], limit: int | None
    ) -> Sequence[Comment]:
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.execute(statement)
        rows = cast("list[CommentRow]", list(result.scalars().all()))
        return [_to_comment(row) for row in rows]

    async def _count(self, *conditions: ColumnElement[bool]) -> int:
        statement = select(func.count()).select_from(CommentRow).where(*conditions)
        return int((await self._session.execute(statement)).scalar_one())


class SqlWatchedEpisodeRepository(WatchedEpisodeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, watched: WatchedEpisode) -> None:
        existing = await self._session.get(
            WatchedEpisodeRow, (watched.viewer_id.value, watched.episode_id.value)
        )
        if existing is None:
            self._session.add(
                WatchedEpisodeRow(
                    viewer_id=watched.viewer_id.value,
                    episode_id=watched.episode_id.value,
                    series_id=watched.series_id.value,
                    watched_at=watched.watched_at,
                )
            )
        else:
            existing.series_id = watched.series_id.value
            existing.watched_at = watched.watched_at
        await self._session.flush()

    async def remove(self, viewer_id: ViewerId, episode_id: EpisodeId) -> None:
        await self._session.execute(
            delete(WatchedEpisodeRow).where(
                WatchedEpisodeRow.viewer_id == viewer_id.value,
                WatchedEpisodeRow.episode_id == episode_id.value,
            )
        )

    async def exists(self, viewer_id: ViewerId, episode_id: EpisodeId) -> bool:
        row = await self._session.get(
            WatchedEpisodeRow, (viewer_id.value, episode_id.value)
        )
        return row is not None

    async def list_episode_ids(
        self, viewer_id: ViewerId, series_id: SeriesId
    ) -> frozenset[EpisodeId]:
        statement = select(WatchedEpisodeRow.episode_id).where(
            WatchedEpisodeRow.viewer_id == viewer_id.value,
            WatchedEpisodeRow.series_id == series_id.value,
        )
        rows = (await self._session.execute(statement)).scalars().all()
        return frozenset(EpisodeId(row) for row in rows)


def _to_insight(row: InsightRow) -> StoredInsight:
    return StoredInsight(
        target=ContentTarget(row.target),
        target_id=row.target_id,
        text=row.text,
        provider=row.provider,
        degraded=row.degraded,
        based_on_comment_count=row.based_on_comment_count,
        generated_at=row.generated_at,
    )


class SqlInsightRepository(InsightRepository):
    """One row per subject: the insight *is* the cache, with its provenance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, target: ContentTarget, target_id: int) -> StoredInsight | None:
        row = await self._session.get(InsightRow, (target.value, target_id))
        return _to_insight(row) if row is not None else None

    async def save(self, insight: StoredInsight) -> StoredInsight:
        key = (insight.target.value, insight.target_id)
        existing = await self._session.get(InsightRow, key)
        if existing is None:
            self._session.add(
                InsightRow(
                    target=insight.target.value,
                    target_id=insight.target_id,
                    text=insight.text,
                    provider=insight.provider,
                    degraded=insight.degraded,
                    based_on_comment_count=insight.based_on_comment_count,
                    generated_at=insight.generated_at,
                )
            )
        else:
            existing.text = insight.text
            existing.provider = insight.provider
            existing.degraded = insight.degraded
            existing.based_on_comment_count = insight.based_on_comment_count
            existing.generated_at = insight.generated_at
        await self._session.flush()
        return insight
