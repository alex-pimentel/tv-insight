"""Level 2: series detail aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.conftest import SERIES_ID, VIEWER
from tests.fakes import (
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
)
from tv_insight.application.errors import InvalidInput, ResourceNotFound
from tv_insight.application.use_cases import GetSeriesDetails
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.services.watch_progress import WatchProgressService
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    ViewerId,
)

MOMENT = datetime(2024, 1, 1, tzinfo=UTC)


def build_use_case(
    gateway: InMemoryTvMazeGateway, uow: InMemoryUnitOfWork
) -> GetSeriesDetails:
    return GetSeriesDetails(gateway, lambda: uow, WatchProgressService())


async def test_detail_groups_episodes_into_seasons(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    detail = await build_use_case(gateway, unit_of_work).execute(SERIES_ID.value, VIEWER)

    assert detail.series.name == "Breaking Bad"
    assert [season.number for season in detail.seasons] == [1, 2]
    assert detail.total_episodes == 4
    assert detail.progress == 0.0


async def test_summary_is_plain_text(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    detail = await build_use_case(gateway, unit_of_work).execute(SERIES_ID.value, VIEWER)
    assert detail.summary == "A chemistry teacher turns to crime."


async def test_watched_state_is_reflected(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    viewer = ViewerId(VIEWER)
    for episode_id in (101, 102, 201):
        await unit_of_work.watches.save(
            WatchedEpisode(
                viewer_id=viewer,
                series_id=SERIES_ID,
                episode_id=EpisodeId(episode_id),
                watched_at=MOMENT,
            )
        )

    detail = await build_use_case(gateway, unit_of_work).execute(SERIES_ID.value, VIEWER)

    assert detail.watched == 3
    assert detail.progress == 0.75
    first_season = detail.seasons[0]
    assert first_season.watched == 2
    assert first_season.progress == 1.0
    assert all(episode.watched for episode in first_season.episodes)
    assert detail.seasons[1].episodes[0].watched is True
    assert detail.seasons[1].episodes[1].watched is False


async def test_watched_state_is_per_viewer(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    await unit_of_work.watches.save(
        WatchedEpisode(
            viewer_id=ViewerId("someone-else"),
            series_id=SERIES_ID,
            episode_id=EpisodeId(101),
            watched_at=MOMENT,
        )
    )

    detail = await build_use_case(gateway, unit_of_work).execute(SERIES_ID.value, VIEWER)

    assert detail.watched == 0


async def test_comments_are_attached_and_counted(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    uow = unit_of_work
    await uow.comments.add(
        Comment(
            id="c1",
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.SERIES,
            series_id=SERIES_ID,
            text=CommentText("Loved it"),
            created_at=MOMENT,
        )
    )
    await uow.comments.add(
        Comment(
            id="c2",
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.EPISODE,
            series_id=SERIES_ID,
            episode_id=EpisodeId(101),
            text=CommentText("Great pilot"),
            created_at=MOMENT,
        )
    )

    detail = await build_use_case(gateway, uow).execute(SERIES_ID.value, VIEWER)

    assert detail.comment_count == 1  # only series level comments
    assert [comment.text for comment in detail.comments] == ["Loved it"]
    assert detail.comments[0].mine is True


async def test_unknown_series_raises_not_found(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    with pytest.raises(ResourceNotFound):
        await build_use_case(gateway, unit_of_work).execute(424242, VIEWER)


async def test_invalid_viewer_is_rejected(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
) -> None:
    with pytest.raises(InvalidInput):
        await build_use_case(gateway, unit_of_work).execute(SERIES_ID.value, "   ")
