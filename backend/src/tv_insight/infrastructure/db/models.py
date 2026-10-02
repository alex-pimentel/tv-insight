"""ORM models.

Two tables are enough for the assignment:

* ``comments`` - a comment belongs either to a series or to an episode;
* ``watched_episodes`` - one row per (viewer, episode) pair, which makes marking
  idempotent for free thanks to the composite primary key.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from tv_insight.infrastructure.db.base import Base

COMMENT_TARGET_MAX = 16
VIEWER_ID_MAX = 64
COMMENT_ID_MAX = 64
PROVIDER_NAME_MAX = 64


class CommentRow(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(COMMENT_ID_MAX), primary_key=True)
    viewer_id: Mapped[str] = mapped_column(String(VIEWER_ID_MAX), index=True)
    target: Mapped[str] = mapped_column(String(COMMENT_TARGET_MAX))
    series_id: Mapped[int] = mapped_column(Integer, index=True)
    episode_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (
        Index("ix_comments_series_target_created", "series_id", "target", "created_at"),
        Index("ix_comments_episode_created", "episode_id", "created_at"),
    )


class WatchedEpisodeRow(Base):
    __tablename__ = "watched_episodes"

    viewer_id: Mapped[str] = mapped_column(String(VIEWER_ID_MAX), primary_key=True)
    episode_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, index=True)
    watched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_watched_viewer_series", "viewer_id", "series_id"),)


class InsightRow(Base):
    """The stored insight and the reason it is still valid.

    Primary key is the subject itself: one insight per series, one per episode.
    ``based_on_comment_count`` is what makes the freshness rule possible without a
    clock - the row records how many comments the text was built from.
    """

    __tablename__ = "insights"

    target: Mapped[str] = mapped_column(String(COMMENT_TARGET_MAX), primary_key=True)
    target_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(PROVIDER_NAME_MAX))
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    based_on_comment_count: Mapped[int] = mapped_column(Integer, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
