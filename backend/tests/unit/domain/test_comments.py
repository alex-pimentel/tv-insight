"""Level 1: the ``Comment`` entity and its target invariant."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)

NOW = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


def build(**overrides: object) -> Comment:
    payload: dict[str, object] = {
        "id": "c1",
        "viewer_id": ViewerId("viewer-a"),
        "target": ContentTarget.SERIES,
        "series_id": SeriesId(1),
        "text": CommentText("Nice"),
        "created_at": NOW,
    }
    payload.update(overrides)
    return Comment(**payload)  # type: ignore[arg-type]


def test_a_series_comment_has_no_episode() -> None:
    comment = build()

    assert comment.target is ContentTarget.SERIES
    assert comment.episode_id is None
    assert comment.is_episode_level is False


def test_an_episode_comment_requires_and_keeps_the_episode() -> None:
    comment = build(target=ContentTarget.EPISODE, episode_id=EpisodeId(42))

    assert comment.target is ContentTarget.EPISODE
    assert comment.episode_id == EpisodeId(42)
    assert comment.is_episode_level is True


def test_comment_ids_are_opaque_strings() -> None:
    assert build(id="abc").id == "abc"


def test_an_empty_comment_id_is_rejected() -> None:
    with pytest.raises(InvalidValue):
        build(id="   ")


def test_a_naive_timestamp_is_rejected() -> None:
    with pytest.raises(InvalidValue):
        build(created_at=datetime(2024, 1, 1, 12, 0))


def test_an_episode_comment_without_an_episode_is_rejected() -> None:
    with pytest.raises(InvalidValue):
        build(target=ContentTarget.EPISODE)


def test_a_series_comment_pointing_at_an_episode_is_rejected() -> None:
    with pytest.raises(InvalidValue):
        build(target=ContentTarget.SERIES, episode_id=EpisodeId(7))


def test_the_validated_comment_text_is_preserved() -> None:
    comment = build(text=CommentText("  spaced   out  "))
    assert comment.text.value == "spaced out"


def test_target_values_are_stable_strings() -> None:
    # The API and the database both persist this value, so it is part of the
    # contract and must not change silently.
    assert ContentTarget.SERIES.value == "series"
    assert ContentTarget.EPISODE.value == "episode"
    assert ContentTarget("series") is ContentTarget.SERIES


def test_comments_are_immutable() -> None:
    comment = build()
    with pytest.raises(AttributeError):
        comment.text = CommentText("other")  # type: ignore[misc]
