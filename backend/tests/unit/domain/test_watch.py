"""Level 2: the watcher's "seen" record."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import EpisodeId, SeriesId, ViewerId

NOW = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


def test_a_watch_record_keeps_the_whole_coordinate() -> None:
    record = WatchedEpisode(
        viewer_id=ViewerId("viewer-a"),
        series_id=SeriesId(1),
        episode_id=EpisodeId(42),
        watched_at=NOW,
    )

    assert record.viewer_id == ViewerId("viewer-a")
    assert record.series_id == SeriesId(1)
    assert record.episode_id == EpisodeId(42)
    assert record.watched_at == NOW


def test_a_naive_timestamp_is_rejected() -> None:
    with pytest.raises(InvalidValue):
        WatchedEpisode(
            viewer_id=ViewerId("viewer-a"),
            series_id=SeriesId(1),
            episode_id=EpisodeId(42),
            watched_at=datetime(2024, 1, 1, 12, 0),
        )


def test_records_compare_by_value() -> None:
    first = WatchedEpisode(ViewerId("v"), SeriesId(1), EpisodeId(9), NOW)
    second = WatchedEpisode(ViewerId("v"), SeriesId(1), EpisodeId(9), NOW)

    assert first == second
    assert hash(first) == hash(second)
