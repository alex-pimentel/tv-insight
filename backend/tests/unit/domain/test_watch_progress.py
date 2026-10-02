"""Level 1: watch progress is pure arithmetic."""

from __future__ import annotations

from collections.abc import Sequence

from tests.conftest import EPISODE_IDS, SERIES_ID
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.services.watch_progress import WatchProgressService
from tv_insight.domain.value_objects import EpisodeId

service = WatchProgressService()


def _guide(episodes: Sequence[Episode]) -> EpisodeGuide:
    return EpisodeGuide.from_episodes(SERIES_ID, list(episodes))


def test_nothing_watched(episodes: Sequence[Episode]) -> None:
    summary = service.summarize(_guide(episodes), frozenset())

    assert summary.watched == 0
    assert summary.total == 4
    assert summary.ratio == 0.0
    assert summary.is_complete is False
    assert [season.watched for season in summary.seasons] == [0, 0]


def test_partial_progress_is_split_per_season(episodes: Sequence[Episode]) -> None:
    watched = frozenset({EpisodeId(101), EpisodeId(102), EpisodeId(201)})

    summary = service.summarize(_guide(episodes), watched)

    assert summary.watched == 3
    assert summary.ratio == 0.75
    first, second = summary.seasons
    assert (first.watched, first.total, first.is_complete) == (2, 2, True)
    assert (second.watched, second.total, second.is_complete) == (1, 2, False)
    assert second.is_started is True


def test_complete_guide(episodes: Sequence[Episode]) -> None:
    summary = service.summarize(_guide(episodes), frozenset(EPISODE_IDS))

    assert summary.is_complete is True
    assert all(season.is_complete for season in summary.seasons)


def test_unknown_episode_ids_are_ignored(episodes: Sequence[Episode]) -> None:
    watched = frozenset({EpisodeId(999), EpisodeId(101)})

    summary = service.summarize(_guide(episodes), watched)

    assert summary.watched == 1
    assert summary.total == 4


def test_empty_guide_does_not_divide_by_zero() -> None:
    summary = service.summarize(_guide([]), frozenset())
    assert summary.ratio == 0.0
    assert summary.is_complete is False


def test_labels_are_human_readable(episodes: Sequence[Episode]) -> None:
    summary = service.summarize(_guide(episodes), frozenset())
    assert [season.label for season in summary.seasons] == ["Season 1", "Season 2"]
