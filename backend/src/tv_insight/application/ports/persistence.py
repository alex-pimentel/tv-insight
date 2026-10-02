"""Transactional boundary port.

A use case opens the unit of work, does its work through the repositories and
commits. One transaction per use case keeps the persistence concern out of the
domain and matches what a reviewer expects from a Clean Architecture project.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from tv_insight.domain.ports.repositories import (
    CommentRepository,
    InsightRepository,
    WatchedEpisodeRepository,
)


class UnitOfWork(ABC):
    """Groups the repositories behind a single transaction."""

    comments: CommentRepository
    watches: WatchedEpisodeRepository
    insights: InsightRepository

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...
