"""Shared fixtures.

Everything here is in-memory: the unit and integration suites run with no
network, no database and no LLM, which is what makes them fast enough to run on
every commit.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from datetime import date
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:  # pragma: no cover - import bootstrap
    sys.path.insert(0, str(SRC))

from tests.fakes import (  # noqa: E402
    FixedClock,
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
    ScriptedInsightProvider,
)
from tv_insight.domain.entities.episode import Episode  # noqa: E402
from tv_insight.domain.entities.series import Series  # noqa: E402
from tv_insight.domain.value_objects import (  # noqa: E402
    EpisodeId,
    EpisodeNumber,
    Genre,
    Rating,
    SeasonNumber,
    SeriesId,
)

SERIES_ID = SeriesId(1)
OTHER_SERIES_ID = SeriesId(2)
EPISODE_IDS = (EpisodeId(101), EpisodeId(102), EpisodeId(201), EpisodeId(202))
VIEWER = "viewer-abc"


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def breaking_bad() -> Series:
    return Series(
        id=SERIES_ID,
        name="Breaking Bad",
        summary="<p>A chemistry teacher turns to <b>crime</b>.</p>",
        genres=(Genre("Drama"), Genre("Crime")),
        premiered=date(2008, 1, 20),
        ended=date(2013, 9, 29),
        status="Ended",
        poster_url="https://example.test/bb.jpg",
        poster_thumbnail_url="https://example.test/bb-thumb.jpg",
        network="AMC",
        rating=Rating(9.2),
        language="English",
    )


@pytest.fixture
def other_series() -> Series:
    return Series(
        id=OTHER_SERIES_ID,
        name="Better Call Saul",
        genres=(Genre("Drama"),),
        premiered=date(2015, 2, 8),
        status="Ended",
    )


@pytest.fixture
def episodes() -> Sequence[Episode]:
    def build(
        episode_id: int,
        season: int,
        number: int,
        name: str,
        airdate: date,
    ) -> Episode:
        return Episode(
            id=EpisodeId(episode_id),
            series_id=SERIES_ID,
            name=name,
            season=SeasonNumber(season),
            number=EpisodeNumber(number),
            summary=f"<p>{name} summary.</p>",
            airdate=airdate,
            runtime_minutes=47,
            image_url=f"https://example.test/{episode_id}.jpg",
        )

    return (
        build(101, 1, 1, "Pilot", date(2008, 1, 20)),
        build(102, 1, 2, "Cat's in the Bag...", date(2008, 1, 27)),
        build(201, 2, 1, "Seven Thirty-Seven", date(2009, 3, 8)),
        build(202, 2, 2, "Grilled", date(2009, 3, 15)),
    )


@pytest.fixture
def gateway(
    breaking_bad: Series, other_series: Series, episodes: Sequence[Episode]
) -> InMemoryTvMazeGateway:
    return InMemoryTvMazeGateway(
        series=(breaking_bad, other_series),
        episodes={SERIES_ID.value: episodes},
    )


@pytest.fixture
def unit_of_work() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def insight_provider() -> ScriptedInsightProvider:
    return ScriptedInsightProvider(answers=("A gritty character study.",))


@pytest.fixture
def uow_factory(unit_of_work: InMemoryUnitOfWork):  # noqa: ANN201
    def factory() -> InMemoryUnitOfWork:
        return unit_of_work

    return factory


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Keep the ``lru_cache`` on ``get_settings`` from leaking between tests."""
    from tv_insight.infrastructure.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
