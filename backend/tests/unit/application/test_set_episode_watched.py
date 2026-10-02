"""Level 2: watched toggle semantics."""

from __future__ import annotations

import pytest

from tests.conftest import SERIES_ID, VIEWER
from tests.fakes import (
    FixedClock,
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
)
from tv_insight.application.errors import ResourceNotFound
from tv_insight.application.use_cases import SetEpisodeWatched
from tv_insight.domain.value_objects import EpisodeId, ViewerId


def build_use_case(
    gateway: InMemoryTvMazeGateway, uow: InMemoryUnitOfWork, clock: FixedClock
) -> SetEpisodeWatched:
    return SetEpisodeWatched(gateway, lambda: uow, clock)


async def test_marking_persists_and_is_returned(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    use_case = build_use_case(gateway, unit_of_work, clock)

    episode = await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=True)

    assert episode.watched is True
    assert episode.code == "S01E01"
    assert await unit_of_work.watches.exists(ViewerId(VIEWER), EpisodeId(101)) is True
    assert unit_of_work.commits == 1


async def test_marking_twice_is_idempotent(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    use_case = build_use_case(gateway, unit_of_work, clock)

    await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=True)
    await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=True)

    assert len(unit_of_work.watches.rows) == 1


async def test_unmarking_removes_the_row(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    use_case = build_use_case(gateway, unit_of_work, clock)
    await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=True)

    episode = await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=False)

    assert episode.watched is False
    assert unit_of_work.watches.rows == {}


async def test_unmarking_something_never_marked_is_a_no_op(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    await build_use_case(gateway, unit_of_work, clock).execute(
        SERIES_ID.value, 101, VIEWER, watched=False
    )
    assert unit_of_work.watches.rows == {}


async def test_episode_from_another_series_is_refused(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    with pytest.raises(ResourceNotFound):
        await build_use_case(gateway, unit_of_work, clock).execute(
            SERIES_ID.value, 999999, VIEWER, watched=True
        )

    assert unit_of_work.watches.rows == {}


async def test_unknown_series_is_refused(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    with pytest.raises(ResourceNotFound):
        await build_use_case(gateway, unit_of_work, clock).execute(
            424242, 101, VIEWER, watched=True
        )


async def test_gateway_episodes_are_reused_across_toggles(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    use_case = build_use_case(gateway, unit_of_work, clock)
    await use_case.execute(SERIES_ID.value, 101, VIEWER, watched=True)
    await use_case.execute(SERIES_ID.value, 102, VIEWER, watched=True)

    assert gateway.episode_calls == [SERIES_ID.value, SERIES_ID.value]
