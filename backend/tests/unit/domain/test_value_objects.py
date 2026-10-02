"""Level 1: value objects guard their own invariants."""

from __future__ import annotations

import pytest

from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import (
    CommentText,
    EpisodeId,
    EpisodeNumber,
    Genre,
    Rating,
    SearchTerm,
    SeasonNumber,
    SeriesId,
    ViewerId,
)


@pytest.mark.parametrize("value", [0, -1, 1.5])
def test_series_id_rejects_non_positive(value: object) -> None:
    with pytest.raises(InvalidValue):
        SeriesId(value)  # type: ignore[arg-type]


def test_series_id_rejects_bool() -> None:
    with pytest.raises(InvalidValue):
        SeriesId(True)


def test_ids_are_comparable_and_printable() -> None:
    assert SeriesId(7) == SeriesId(7)
    assert str(SeriesId(7)) == "7"
    assert str(EpisodeId(9)) == "9"


def test_season_zero_is_specials() -> None:
    assert SeasonNumber(0).is_specials is True
    assert str(SeasonNumber(0)) == "Specials"
    assert str(SeasonNumber(3)) == "Season 3"


def test_episode_number_rejects_negative() -> None:
    with pytest.raises(InvalidValue):
        EpisodeNumber(-1)


def test_rating_bounds() -> None:
    assert float(Rating(9.9)) == 9.9
    with pytest.raises(InvalidValue):
        Rating(10.1)


def test_genre_is_normalised() -> None:
    assert Genre("  science   fiction ").value == "science fiction"


def test_genre_rejects_blank_and_long_values() -> None:
    with pytest.raises(InvalidValue):
        Genre("   ")
    with pytest.raises(InvalidValue):
        Genre("x" * 61)


def test_comment_text_collapses_whitespace_and_bounds_length() -> None:
    assert CommentText("  great   episode \n indeed ").value == "great episode indeed"
    with pytest.raises(InvalidValue):
        CommentText("   ")
    with pytest.raises(InvalidValue):
        CommentText("x" * 2001)


def test_viewer_id_rejects_empty() -> None:
    with pytest.raises(InvalidValue):
        ViewerId("  ")


@pytest.mark.parametrize("term", ["a", "", "   ", "x" * 101])
def test_search_term_bounds(term: str) -> None:
    with pytest.raises(InvalidValue):
        SearchTerm(term)


def test_search_term_collapses_spaces() -> None:
    assert SearchTerm("  breaking   bad ").value == "breaking bad"


def test_episode_id_rejects_non_positive() -> None:
    with pytest.raises(InvalidValue):
        EpisodeId(-3)


def test_viewer_id_rejects_an_over_long_value() -> None:
    with pytest.raises(InvalidValue):
        ViewerId("x" * 65)


def test_viewer_id_is_trimmed_and_printable() -> None:
    viewer = ViewerId("  viewer-a  ")
    assert viewer.value == "viewer-a"
    assert str(viewer) == "viewer-a"


def test_season_number_rejects_negative() -> None:
    with pytest.raises(InvalidValue):
        SeasonNumber(-1)


def test_episode_number_is_printable() -> None:
    assert str(EpisodeNumber(7)) == "7"


def test_genre_is_printable() -> None:
    assert str(Genre("Drama")) == "Drama"


def test_comment_text_is_printable() -> None:
    assert str(CommentText("hello")) == "hello"


def test_value_objects_are_hashable_so_they_can_be_set_members() -> None:
    ids = {EpisodeId(1), EpisodeId(1), EpisodeId(2)}
    assert len(ids) == 2
    genres = {Genre("Drama"), Genre("Drama")}
    assert len(genres) == 1
