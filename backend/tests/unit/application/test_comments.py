"""Level 2: comment use cases, including validation of the target."""

from __future__ import annotations

import pytest

from tests.conftest import SERIES_ID, VIEWER
from tests.fakes import FixedClock, InMemoryTvMazeGateway, InMemoryUnitOfWork
from tv_insight.application.errors import InvalidInput, ResourceNotFound
from tv_insight.application.use_cases import AddComment, ListComments


def add_use_case(
    gateway: InMemoryTvMazeGateway, uow: InMemoryUnitOfWork, clock: FixedClock
) -> AddComment:
    counter = iter(f"id-{index}" for index in range(100))
    return AddComment(gateway, lambda: uow, clock, new_id=lambda: next(counter))


def list_use_case(
    gateway: InMemoryTvMazeGateway, uow: InMemoryUnitOfWork
) -> ListComments:
    return ListComments(gateway, lambda: uow)


async def test_series_comment_is_stored(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    view = await add_use_case(gateway, unit_of_work, clock).execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER, text="  Great show  "
    )

    assert view.target == "series"
    assert view.text == "Great show"
    assert view.episode_id is None
    assert unit_of_work.commits == 1


async def test_episode_comment_carries_the_episode_code(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    view = await add_use_case(gateway, unit_of_work, clock).execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER, text="Amazing", episode_id=101
    )

    assert view.target == "episode"
    assert view.episode_id == 101
    assert view.episode_code == "S01E01"


async def test_blank_comment_is_rejected(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    with pytest.raises(InvalidInput):
        await add_use_case(gateway, unit_of_work, clock).execute(
            series_id=SERIES_ID.value, viewer_id=VIEWER, text="   "
        )


async def test_comment_on_unknown_series_is_rejected(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    with pytest.raises(ResourceNotFound):
        await add_use_case(gateway, unit_of_work, clock).execute(
            series_id=424242, viewer_id=VIEWER, text="Hello"
        )


async def test_comment_on_foreign_episode_is_rejected(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    with pytest.raises(ResourceNotFound):
        await add_use_case(gateway, unit_of_work, clock).execute(
            series_id=SERIES_ID.value, viewer_id=VIEWER, text="Hi", episode_id=987654
        )


async def test_listing_splits_series_and_episode_comments(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    adder = add_use_case(gateway, unit_of_work, clock)
    await adder.execute(series_id=SERIES_ID.value, viewer_id=VIEWER, text="Series one")
    await adder.execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER, text="Episode one", episode_id=101
    )
    await adder.execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER, text="Episode two", episode_id=101
    )

    lister = list_use_case(gateway, unit_of_work)

    series_comments = await lister.execute(series_id=SERIES_ID.value, viewer_id=VIEWER)
    episode_comments = await lister.execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER, episode_id=101
    )

    assert [comment.text for comment in series_comments] == ["Series one"]
    assert [comment.text for comment in episode_comments] == [
        "Episode two",
        "Episode one",
    ]


async def test_newest_comment_comes_first(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    adder = add_use_case(gateway, unit_of_work, clock)
    await adder.execute(series_id=SERIES_ID.value, viewer_id=VIEWER, text="First")
    await adder.execute(series_id=SERIES_ID.value, viewer_id=VIEWER, text="Second")

    comments = await list_use_case(gateway, unit_of_work).execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER
    )

    assert [comment.text for comment in comments] == ["Second", "First"]


async def test_mine_flag_is_per_viewer(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    await add_use_case(gateway, unit_of_work, clock).execute(
        series_id=SERIES_ID.value, viewer_id="someone-else", text="Not mine"
    )

    comments = await list_use_case(gateway, unit_of_work).execute(
        series_id=SERIES_ID.value, viewer_id=VIEWER
    )

    assert comments[0].mine is False
