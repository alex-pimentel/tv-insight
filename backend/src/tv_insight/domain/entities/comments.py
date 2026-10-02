"""Comments attached either to a series or to a single episode."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)


@dataclass(frozen=True, slots=True)
class Comment:
    """A comment authored by a viewer.

    Invariant: an episode level comment must reference the episode, a series
    level comment must not.
    """

    id: str
    viewer_id: ViewerId
    target: ContentTarget
    series_id: SeriesId
    text: CommentText
    created_at: datetime
    episode_id: EpisodeId | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise InvalidValue("Comment id must not be empty")
        if self.created_at.tzinfo is None:
            raise InvalidValue("Comment.created_at must be timezone aware")
        if self.target is ContentTarget.EPISODE and self.episode_id is None:
            raise InvalidValue("An episode comment must reference an episode")
        if self.target is ContentTarget.SERIES and self.episode_id is not None:
            raise InvalidValue("A series comment must not reference an episode")

    @property
    def is_episode_level(self) -> bool:
        return self.target is ContentTarget.EPISODE
