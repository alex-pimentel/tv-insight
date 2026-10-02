"""Level 2: the insight use case delegates to the provider port."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.conftest import SERIES_ID, VIEWER
from tests.fakes import (
    FixedClock,
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
    ScriptedInsightProvider,
    UnavailableInsightProvider,
)
from tv_insight.application.errors import ProviderUnavailable, ResourceNotFound
from tv_insight.application.use_cases import GenerateInsight
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.services.insight_prompt import InsightPromptComposer
from tv_insight.domain.value_objects import CommentText, ContentTarget, EpisodeId, ViewerId

MOMENT = datetime(2024, 1, 1, tzinfo=UTC)


def build(
    gateway: InMemoryTvMazeGateway,
    uow: InMemoryUnitOfWork,
    provider: object,
    clock: FixedClock,
    *,
    comment_threshold: int = 1,
) -> GenerateInsight:
    return GenerateInsight(
        gateway,
        lambda: uow,
        provider,  # type: ignore[arg-type]
        InsightPromptComposer(),
        clock,
        comment_threshold=comment_threshold,
    )


async def test_series_insight_returns_provider_provenance(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    insight = await build(gateway, unit_of_work, insight_provider, clock).for_series(
        SERIES_ID.value
    )

    assert insight.text == "A gritty character study."
    assert insight.provider == "scripted"
    assert insight.degraded is False
    assert insight.target == "series"
    assert insight.target_id == 1


async def test_prompt_contains_comments(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    await unit_of_work.comments.add(
        Comment(
            id="c1",
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.SERIES,
            series_id=SERIES_ID,
            text=CommentText("The pacing is perfect"),
            created_at=MOMENT,
        )
    )

    await build(gateway, unit_of_work, insight_provider, clock).for_series(SERIES_ID.value)

    request = insight_provider.requests[0]
    assert "- The pacing is perfect" in request.prompt.user
    assert "Genres: Drama, Crime" in request.prompt.user


async def test_episode_insight_uses_episode_context(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    insight = await build(gateway, unit_of_work, insight_provider, clock).for_episode(
        SERIES_ID.value, 201
    )

    assert insight.target == "episode"
    assert insight.target_id == 201
    user = insight_provider.requests[0].prompt.user
    assert "Target: episode" in user
    assert "Episode: S02E01" in user
    assert "Series: Breaking Bad" in user


async def test_episode_insight_falls_back_to_series_comments(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    await unit_of_work.comments.add(
        Comment(
            id="c1",
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.SERIES,
            series_id=SERIES_ID,
            text=CommentText("Whole series is great"),
            created_at=MOMENT,
        )
    )

    await build(gateway, unit_of_work, insight_provider, clock).for_episode(
        SERIES_ID.value, 201
    )

    assert "- Whole series is great" in insight_provider.requests[0].prompt.user


async def test_refresh_is_forwarded_to_the_provider(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    await build(gateway, unit_of_work, insight_provider, clock).for_series(
        SERIES_ID.value, refresh=True
    )
    assert insight_provider.refresh_calls == [True]


async def test_provider_failure_surfaces_as_application_error(
    gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork, clock: FixedClock
) -> None:
    provider = UnavailableInsightProvider()

    with pytest.raises(ProviderUnavailable):
        await build(gateway, unit_of_work, provider, clock).for_series(SERIES_ID.value)


async def test_empty_answer_is_treated_as_a_failure(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    clock: FixedClock,
) -> None:
    provider = ScriptedInsightProvider(answers=("   ",))

    with pytest.raises(ProviderUnavailable):
        await build(gateway, unit_of_work, provider, clock).for_series(SERIES_ID.value)


async def test_unknown_series_is_rejected(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    with pytest.raises(ResourceNotFound):
        await build(gateway, unit_of_work, insight_provider, clock).for_series(424242)


async def test_unknown_episode_is_rejected(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    with pytest.raises(ResourceNotFound):
        await build(gateway, unit_of_work, insight_provider, clock).for_episode(
            SERIES_ID.value, 999999
        )


async def test_episode_comments_take_precedence(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> None:
    await unit_of_work.comments.add(
        Comment(
            id="c1",
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.EPISODE,
            series_id=SERIES_ID,
            episode_id=EpisodeId(201),
            text=CommentText("That cliffhanger"),
            created_at=MOMENT,
        )
    )

    await build(gateway, unit_of_work, insight_provider, clock).for_episode(
        SERIES_ID.value, 201
    )

    assert "- That cliffhanger" in insight_provider.requests[0].prompt.user
