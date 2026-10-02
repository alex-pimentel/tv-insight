"""Level 1: episode grouping and lookup."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

import pytest

from tests.conftest import EPISODE_IDS, SERIES_ID
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.exceptions import NotFound
from tv_insight.domain.value_objects import (
    EpisodeId,
    EpisodeNumber,
    SeasonNumber,
    SeriesId,
)


def _episode(episode_id: int, season: int, number: int) -> Episode:
    return Episode(
        id=EpisodeId(episode_id),
        series_id=SERIES_ID,
        name=f"S{season}E{number}",
        season=SeasonNumber(season),
        number=EpisodeNumber(number),
    )


def test_episode_code_is_zero_padded() -> None:
    assert _episode(1, 2, 7).code == "S02E07"


def test_sort_key_orders_by_season_then_number() -> None:
    assert _episode(1, 1, 9).sort_key() < _episode(2, 2, 1).sort_key()


def test_seasons_group_and_order_episodes(episodes: Sequence[Episode]) -> None:
    guide = EpisodeGuide.from_episodes(SERIES_ID, list(reversed(list(episodes))))

    seasons = guide.seasons()

    assert [season.number.value for season in seasons] == [1, 2]
    assert [episode.name for episode in seasons[0].episodes] == [
        "Pilot",
        "Cat's in the Bag...",
    ]


def test_specials_are_listed_last() -> None:
    guide = EpisodeGuide.from_episodes(
        SERIES_ID,
        [_episode(1, 0, 1), _episode(2, 1, 1), _episode(3, 2, 1)],
    )
    assert [season.number.value for season in guide.seasons()] == [1, 2, 0]


def test_total_and_find() -> None:
    guide = EpisodeGuide.from_episodes(
        SERIES_ID, [_episode(101, 1, 1), _episode(102, 1, 2)]
    )
    assert guide.total_episodes == 2
    assert guide.find(EpisodeId(102)).name == "S1E2"


def test_find_raises_for_foreign_episode() -> None:
    guide = EpisodeGuide.from_episodes(SERIES_ID, [_episode(101, 1, 1)])
    with pytest.raises(NotFound):
        guide.find(EpisodeId(999))


def test_empty_guide_is_valid() -> None:
    guide = EpisodeGuide.from_episodes(SeriesId(9), [])
    assert guide.seasons() == ()
    assert guide.total_episodes == 0


def test_all_episode_ids_are_unique_in_fixture() -> None:
    assert len(set(EPISODE_IDS)) == len(EPISODE_IDS)


def test_episode_synopsis_strips_html() -> None:
    episode = Episode(
        id=EpisodeId(1),
        series_id=SERIES_ID,
        name="Pilot",
        season=SeasonNumber(1),
        number=EpisodeNumber(1),
        summary="<p>Nice <i>start</i>.</p>",
    )
    assert episode.synopsis() == "Nice start."


def test_episode_airdate_is_optional() -> None:
    episode = _episode(1, 1, 1)
    assert episode.airdate is None
    assert isinstance(date.today(), date)
