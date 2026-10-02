"""Transaction boundary implementation.

One ``SqlAlchemyUnitOfWork`` per use case invocation. The repositories share the
same session, so a failure anywhere rolls the whole operation back, and an
exception escaping the ``async with`` block never leaks a half written change.
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.domain.ports.repositories import (
    CommentRepository,
    InsightRepository,
    WatchedEpisodeRepository,
)
from tv_insight.infrastructure.db.repositories import (
    SqlCommentRepository,
    SqlInsightRepository,
    SqlWatchedEpisodeRepository,
)
from tv_insight.infrastructure.db.session import SessionFactory


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.comments: CommentRepository
        self.watches: WatchedEpisodeRepository
        self.insights: InsightRepository

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.comments = SqlCommentRepository(self._session)
        self.watches = SqlWatchedEpisodeRepository(self._session)
        self.insights = SqlInsightRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
