"""Level 1: the ``Series`` entity."""

from __future__ import annotations

from datetime import date

import pytest

from tv_insight.domain.entities.series import Series
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import Genre, Rating, SeriesId


def test_year_prefers_premiere_date() -> None:
    series = Series(
        id=SeriesId(1),
        name="Show",
        premiered=date(2010, 5, 1),
        ended=date(2013, 8, 2),
    )
    assert series.year == 2010


def test_year_falls_back_to_end_date() -> None:
    series = Series(id=SeriesId(1), name="Show", ended=date(2013, 8, 2))
    assert series.year == 2013


def test_year_is_none_without_dates() -> None:
    assert Series(id=SeriesId(1), name="Show").year is None


def test_is_running_recognises_known_statuses() -> None:
    assert Series(id=SeriesId(1), name="Show", status="Running").is_running
    assert not Series(id=SeriesId(1), name="Show", status="Ended").is_running
    assert not Series(id=SeriesId(1), name="Show").is_running


def test_synopsis_strips_html() -> None:
    series = Series(
        id=SeriesId(1),
        name="Show",
        summary="<p>Hello <b>world</b> &amp; friends</p>",
    )
    assert series.synopsis() == "Hello world &amp; friends"


def test_synopsis_falls_back_when_missing() -> None:
    series = Series(id=SeriesId(1), name="Show", summary=None)
    assert series.synopsis() == "No summary available for this series."


def test_genre_names_exposes_plain_strings() -> None:
    series = Series(
        id=SeriesId(1), name="Show", genres=(Genre("Drama"), Genre("Crime"))
    )
    assert series.genre_names == ("Drama", "Crime")


def test_rating_is_optional_but_typed() -> None:
    series = Series(id=SeriesId(1), name="Show", rating=Rating(8.5))
    assert float(series.rating) == 8.5 if series.rating else False


def test_name_cannot_be_blank() -> None:
    with pytest.raises(InvalidValue):
        Series(id=SeriesId(1), name="   ")


def test_entities_are_immutable() -> None:
    series = Series(id=SeriesId(1), name="Show")
    with pytest.raises(AttributeError):
        series.name = "Other"  # type: ignore[misc]
