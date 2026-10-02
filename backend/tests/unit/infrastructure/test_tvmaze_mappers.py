"""Level 3: JSON payload -> domain mapping, without any HTTP."""

from __future__ import annotations

import pytest

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import SeriesId
from tv_insight.infrastructure.tvmaze.mappers import (
    genres_from,
    parse_date,
    poster_from,
    poster_thumbnail_from,
    rating_from,
    to_episode,
    to_series,
)

SHOW = {
    "id": 1,
    "name": "Breaking Bad",
    "summary": "<p>Crime drama.</p>",
    "genres": ["Drama", "Crime"],
    "premiered": "2008-01-20",
    "ended": "2013-09-29",
    "status": "Ended",
    "image": {"medium": "m.jpg", "original": "o.jpg"},
    "network": {"name": "AMC"},
    "rating": {"average": 9.2},
    "language": "English",
    "officialSite": "https://amc.test/bb",
}


def test_to_series_maps_every_field() -> None:
    series = to_series(SHOW)

    assert series.id == SeriesId(1)
    assert series.name == "Breaking Bad"
    assert series.genre_names == ("Drama", "Crime")
    assert series.poster_url == "o.jpg"
    assert series.poster_thumbnail_url == "m.jpg"
    assert series.network == "AMC"
    assert series.status == "Ended"
    assert series.language == "English"
    assert float(series.rating) == 9.2
    assert series.year == 2008
    assert series.synopsis() == "Crime drama."


def test_webchannel_is_used_when_network_is_missing() -> None:
    payload = dict(SHOW, network=None, webChannel={"name": "Netflix"})
    assert to_series(payload).network == "Netflix"


def test_missing_optional_fields_are_tolerated() -> None:
    series = to_series({"id": 5, "name": "Minimal"})

    assert series.summary is None
    assert series.genres == ()
    assert series.rating is None
    assert series.year is None
    assert series.is_running is False


def test_invalid_genres_do_not_break_the_mapping() -> None:
    payload = dict(SHOW, genres=["Drama", "", "   ", "x" * 80])
    assert to_series(payload).genre_names == ("Drama",)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No id"},
        {"id": 0, "name": "Zero"},
        {"id": 1},
        {"id": 1, "name": "   "},
    ],
)
def test_invalid_show_payloads_are_rejected(payload: dict) -> None:
    with pytest.raises(InvalidValue):
        to_series(payload)


def test_to_episode_maps_and_defaults() -> None:
    episode = to_episode(
        {
            "id": 501,
            "name": "Pilot",
            "season": 1,
            "number": 1,
            "summary": "<p>Start.</p>",
            "airdate": "2008-01-20",
            "runtime": 58,
            "image": {"original": "e.jpg"},
        },
        SeriesId(1),
    )

    assert episode.code == "S01E01"
    assert episode.runtime_minutes == 58
    assert episode.airdate is not None
    assert episode.synopsis() == "Start."


def test_to_episode_names_unnamed_episodes() -> None:
    episode = to_episode({"id": 7, "season": 2, "number": 3}, SeriesId(1))
    assert episode.name == "Episode 3"


def test_to_episode_requires_an_id() -> None:
    with pytest.raises(InvalidValue):
        to_episode({"name": "x", "season": 1, "number": 1}, SeriesId(1))


def test_negative_season_and_number_are_clamped() -> None:
    episode = to_episode({"id": 8, "season": -1, "number": -4}, SeriesId(1))
    assert episode.season.value == 0
    assert episode.number.value == 0


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2013-04-14", 2013),
        ("2013-04-14T00:00:00+00:00", 2013),
        ("", None),
        (None, None),
        ("not-a-date", None),
    ],
)
def test_parse_date(raw: object, expected: int | None) -> None:
    parsed = parse_date(raw)
    assert (parsed.year if parsed else None) == expected


def test_poster_falls_back_to_medium() -> None:
    assert poster_from({"medium": "m.jpg"}) == "m.jpg"
    assert poster_from(None) is None
    assert poster_from({}) is None


def test_poster_thumbnail_prefers_medium() -> None:
    # The small card image is `medium`; `original` is only a fallback.
    assert poster_thumbnail_from({"medium": "m.jpg", "original": "o.jpg"}) == "m.jpg"
    assert poster_thumbnail_from({"original": "o.jpg"}) == "o.jpg"
    assert poster_thumbnail_from(None) is None
    assert poster_thumbnail_from({}) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"average": 7.5}, 7.5),
        ({"average": None}, None),
        ({}, None),
        (None, None),
        ({"average": 11.0}, None),
    ],
)
def test_rating_from(raw: object, expected: float | None) -> None:
    rating = rating_from(raw)
    assert (float(rating) if rating else None) == expected


def test_genres_from_ignores_non_sequences() -> None:
    assert genres_from("Drama") == ()
    assert genres_from(None) == ()
