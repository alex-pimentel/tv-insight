"""Pure functions mapping TVMaze JSON payloads onto domain entities.

Kept separate from the client so the payload shape is testable without any HTTP,
and so a change in the catalogue's JSON touches exactly one file.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.series import Series
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import (
    EpisodeId,
    EpisodeNumber,
    Genre,
    Rating,
    SeasonNumber,
    SeriesId,
)

_Image = Mapping[str, Any] | None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def parse_date(value: Any) -> date | None:
    """TVMaze uses ``YYYY-MM-DD``; empty strings and nulls mean "unknown"."""
    raw = _as_str(value)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def poster_from(image: _Image) -> str | None:
    """The largest image available: the detail header uses this one."""
    data = _as_mapping(image)
    return _as_str(data.get("original")) or _as_str(data.get("medium"))


def poster_thumbnail_from(image: _Image) -> str | None:
    """The small image: search result cards use this one instead of the original.

    TVMaze only publishes ``medium`` and ``original``; ``medium`` is the smaller of
    the two, so it is what a grid of small cards should download. Falls back to
    ``original`` for payloads that omit ``medium``.
    """
    data = _as_mapping(image)
    return _as_str(data.get("medium")) or _as_str(data.get("original"))


def genres_from(raw: Any) -> tuple[Genre, ...]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    genres: list[Genre] = []
    for item in raw:
        try:
            genres.append(Genre(str(item)))
        except InvalidValue:
            continue
    return tuple(genres)


def rating_from(raw: Any) -> Rating | None:
    data = _as_mapping(raw)
    average = data.get("average")
    if isinstance(average, bool) or not isinstance(average, (int, float)):
        return None
    try:
        return Rating(float(average))
    except InvalidValue:
        return None


def to_series(payload: Mapping[str, Any]) -> Series:
    """Map a TVMaze ``show`` object onto a ``Series``."""
    series_id = _as_int(payload.get("id"))
    name = _as_str(payload.get("name"))
    if series_id is None or series_id <= 0:
        raise InvalidValue("TVMaze show payload without a valid id")
    if name is None:
        raise InvalidValue("TVMaze show payload without a name")

    network = _as_str(_as_mapping(payload.get("network")).get("name")) or _as_str(
        _as_mapping(payload.get("webChannel")).get("name")
    )

    return Series(
        id=SeriesId(series_id),
        name=name,
        summary=_as_str(payload.get("summary")),
        genres=genres_from(payload.get("genres")),
        premiered=parse_date(payload.get("premiered")),
        ended=parse_date(payload.get("ended")),
        status=_as_str(payload.get("status")),
        poster_url=poster_from(payload.get("image")),
        poster_thumbnail_url=poster_thumbnail_from(payload.get("image")),
        network=network,
        rating=rating_from(payload.get("rating")),
        language=_as_str(payload.get("language")),
        official_url=_as_str(payload.get("officialSite")) or _as_str(payload.get("url")),
    )


def to_episode(payload: Mapping[str, Any], series_id: SeriesId) -> Episode:
    """Map a TVMaze ``episode`` object onto an ``Episode``."""
    episode_id = _as_int(payload.get("id"))
    if episode_id is None or episode_id <= 0:
        raise InvalidValue("TVMaze episode payload without a valid id")

    return Episode(
        id=EpisodeId(episode_id),
        series_id=series_id,
        name=_as_str(payload.get("name")) or f"Episode {_as_int(payload.get('number')) or '?'}",
        season=SeasonNumber(max(_as_int(payload.get("season")) or 0, 0)),
        number=EpisodeNumber(max(_as_int(payload.get("number")) or 0, 0)),
        summary=_as_str(payload.get("summary")),
        airdate=parse_date(payload.get("airdate")),
        runtime_minutes=_as_int(payload.get("runtime")),
        image_url=poster_from(payload.get("image")),
    )
