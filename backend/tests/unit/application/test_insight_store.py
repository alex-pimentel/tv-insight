"""Level 2: the insight decision matrix.

    1. every explicit request tries the model providers first;
    2. if they fail and a stored insight exists, the stored one is served;
    3. if they fail and the store is empty, the heuristic tier answers.

Cost control (reuse until N new comments) is opt-in via ``comment_threshold``; the
default of ``0`` disables it, which is why "generate" here really means "call the
provider".
"""

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
from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.use_cases import GenerateInsight
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.services.insight_prompt import InsightPromptComposer
from tv_insight.domain.value_objects import CommentText, ContentTarget, EpisodeId, ViewerId
from tv_insight.infrastructure.ai.fallback import FallbackInsightProvider
from tv_insight.infrastructure.ai.heuristic import HeuristicInsightProvider

MOMENT = datetime(2024, 1, 1, tzinfo=UTC)
NO_REUSE = 0
REUSE_AFTER_ONE_COMMENT = 1


def build(
    gateway: InMemoryTvMazeGateway,
    uow: InMemoryUnitOfWork,
    provider: object,
    clock: FixedClock,
    *,
    threshold: int = NO_REUSE,
) -> GenerateInsight:
    return GenerateInsight(
        gateway,
        lambda: uow,
        provider,  # type: ignore[arg-type]
        InsightPromptComposer(),
        clock,
        comment_threshold=threshold,
    )


def model_then_heuristic(heuristic: HeuristicInsightProvider) -> FallbackInsightProvider:
    """A chain whose model tier is down, so the heuristic answers."""
    return FallbackInsightProvider([UnavailableInsightProvider(name="model"), heuristic])


async def add_series_comment(uow: InMemoryUnitOfWork, identifier: str, text: str) -> None:
    await uow.comments.add(
        Comment(
            id=identifier,
            viewer_id=ViewerId(VIEWER),
            target=ContentTarget.SERIES,
            series_id=SERIES_ID,
            text=CommentText(text),
            created_at=MOMENT,
        )
    )


class TestEveryRequestGenerates:
    """Rule 1: the model is called on every explicit request by default."""

    async def test_two_consecutive_requests_call_the_provider_twice(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("first answer", "second answer"))
        use_case = build(gateway, unit_of_work, provider, clock)

        first = await use_case.for_series(SERIES_ID.value)
        second = await use_case.for_series(SERIES_ID.value)

        assert first.text == "first answer"
        assert second.text == "second answer"
        assert first.cached is False
        assert second.cached is False
        assert len(provider.requests) == 2

    async def test_the_fresh_answer_is_persisted_for_later(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("a model answer",))
        view = await build(gateway, unit_of_work, provider, clock).for_series(
            SERIES_ID.value
        )

        stored = await unit_of_work.insights.get(ContentTarget.SERIES, SERIES_ID.value)

        assert stored is not None
        assert stored.text == view.text
        assert stored.provider == "scripted"
        assert stored.degraded is False
        assert unit_of_work.commits == 1

    async def test_two_requests_generate_two_prompts(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("one", "two"))
        use_case = build(gateway, unit_of_work, provider, clock)

        await use_case.for_series(SERIES_ID.value)
        await use_case.for_series(SERIES_ID.value)

        assert len(provider.requests) == 2


class TestStoredAnswerIsTheSafetyNet:
    """Rules 2 and 3: the store is preferred over the heuristic, and it is only
    ever filled with answers a real model produced."""

    async def test_only_model_answers_are_persisted(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        use_case = build(
            gateway, unit_of_work, model_then_heuristic(HeuristicInsightProvider()), clock
        )

        view = await use_case.for_series(SERIES_ID.value)

        assert view.degraded is True
        assert view.provider == "heuristic"
        # The heuristic must never occupy the "last known good" slot.
        assert unit_of_work.insights.rows == {}
        assert unit_of_work.commits == 0

    async def test_a_model_failure_prefers_the_stored_answer_over_the_heuristic(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        # 1. A model answers once, so the store holds a real insight.
        await build(
            gateway, unit_of_work, ScriptedInsightProvider(answers=("from the model",)), clock
        ).for_series(SERIES_ID.value)

        # 2. The model tier is now down; the chain would answer with the heuristic.
        view = await build(
            gateway, unit_of_work, model_then_heuristic(HeuristicInsightProvider()), clock
        ).for_series(SERIES_ID.value)

        assert view.text == "from the model"
        assert view.provider == "scripted"
        assert view.cached is True
        assert view.degraded is True
        assert any("last stored" in note for note in view.notes)

    async def test_without_a_stored_answer_the_heuristic_is_used(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        use_case = build(
            gateway, unit_of_work, model_then_heuristic(HeuristicInsightProvider()), clock
        )

        view = await use_case.for_series(SERIES_ID.value)

        assert view.provider == "heuristic"
        assert view.degraded is True
        assert view.text.strip()

    async def test_a_chain_that_fails_entirely_uses_the_stored_answer(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        await build(
            gateway, unit_of_work, ScriptedInsightProvider(answers=("saved",)), clock
        ).for_series(SERIES_ID.value)

        view = await build(
            gateway, unit_of_work, UnavailableInsightProvider(), clock
        ).for_series(SERIES_ID.value)

        assert view.text == "saved"
        assert view.cached is True
        assert any("last stored" in note for note in view.notes)

    async def test_a_chain_that_fails_with_an_empty_store_surfaces_the_error(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        with pytest.raises(ProviderUnavailable):
            await build(
                gateway, unit_of_work, UnavailableInsightProvider(), clock
            ).for_series(SERIES_ID.value)

    async def test_an_empty_model_answer_falls_back_to_the_stored_answer(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        await build(
            gateway, unit_of_work, ScriptedInsightProvider(answers=("saved",)), clock
        ).for_series(SERIES_ID.value)

        view = await build(
            gateway, unit_of_work, ScriptedInsightProvider(answers=("   ",)), clock
        ).for_series(SERIES_ID.value)

        assert view.text == "saved"
        assert any("nothing" in note for note in view.notes)

    async def test_the_stored_answer_is_not_overwritten_by_a_heuristic(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        await build(
            gateway, unit_of_work, ScriptedInsightProvider(answers=("the good one",)), clock
        ).for_series(SERIES_ID.value)

        await build(
            gateway, unit_of_work, model_then_heuristic(HeuristicInsightProvider()), clock
        ).for_series(SERIES_ID.value)

        stored = await unit_of_work.insights.get(ContentTarget.SERIES, SERIES_ID.value)
        assert stored is not None and stored.text == "the good one"


class TestOptionalReuseWindow:
    """The cost-control rule stays available, but opt-in (threshold > 0)."""

    async def test_within_the_window_the_provider_is_not_called(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("one", "two"))
        use_case = build(
            gateway,
            unit_of_work,
            provider,
            clock,
            threshold=REUSE_AFTER_ONE_COMMENT,
        )

        first = await use_case.for_series(SERIES_ID.value)
        second = await use_case.for_series(SERIES_ID.value)

        assert first.cached is False
        assert second.cached is True
        assert second.text == "one"
        assert len(provider.requests) == 1

    async def test_one_new_comment_reopens_the_window(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("before", "after"))
        use_case = build(
            gateway,
            unit_of_work,
            provider,
            clock,
            threshold=REUSE_AFTER_ONE_COMMENT,
        )

        await use_case.for_series(SERIES_ID.value)
        await add_series_comment(unit_of_work, "c1", "a new opinion")
        view = await use_case.for_series(SERIES_ID.value)

        assert view.text == "after"
        assert view.cached is False
        assert len(provider.requests) == 2

    async def test_a_greater_threshold_requires_more_comments(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("first", "second"))
        use_case = build(gateway, unit_of_work, provider, clock, threshold=3)

        await use_case.for_series(SERIES_ID.value)
        await add_series_comment(unit_of_work, "c1", "one")
        cached = await use_case.for_series(SERIES_ID.value)

        assert cached.cached is True
        assert len(provider.requests) == 1

    async def test_refresh_bypasses_the_window(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("first", "second"))
        use_case = build(
            gateway,
            unit_of_work,
            provider,
            clock,
            threshold=REUSE_AFTER_ONE_COMMENT,
        )

        await use_case.for_series(SERIES_ID.value)
        refreshed = await use_case.for_series(SERIES_ID.value, refresh=True)

        assert refreshed.text == "second"
        assert refreshed.cached is False
        assert len(provider.requests) == 2

    async def test_the_window_also_applies_to_episode_insights(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("one", "two"))
        use_case = build(
            gateway,
            unit_of_work,
            provider,
            clock,
            threshold=REUSE_AFTER_ONE_COMMENT,
        )

        first = await use_case.for_episode(SERIES_ID.value, 201)
        second = await use_case.for_episode(SERIES_ID.value, 201)

        assert first.cached is False
        assert second.cached is True
        assert second.text == "one"
        assert len(provider.requests) == 1

    async def test_a_new_comment_changes_the_prompt(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("first", "second"))
        use_case = build(
            gateway,
            unit_of_work,
            provider,
            clock,
            threshold=REUSE_AFTER_ONE_COMMENT,
        )

        await use_case.for_series(SERIES_ID.value)
        await add_series_comment(unit_of_work, "c1", "the pacing is great")
        await use_case.for_series(SERIES_ID.value)

        assert "the pacing is great" in provider.requests[1].prompt.user
        assert "the pacing is great" not in provider.requests[0].prompt.user


class TestSubjectIsolation:
    async def test_series_and_episode_insights_have_separate_slots(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("series", "episode"))
        use_case = build(gateway, unit_of_work, provider, clock)

        await use_case.for_series(SERIES_ID.value)
        episode_view = await use_case.for_episode(SERIES_ID.value, 201)

        assert episode_view.text == "episode"
        assert len(provider.requests) == 2
        assert await unit_of_work.insights.get(ContentTarget.EPISODE, 201) is not None
        assert await unit_of_work.insights.get(ContentTarget.SERIES, SERIES_ID.value) is not None

    async def test_an_episode_insight_uses_the_series_conversation_as_baseline(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        await add_series_comment(unit_of_work, "c1", "about the series")
        provider = ScriptedInsightProvider(answers=("one",))
        use_case = build(gateway, unit_of_work, provider, clock)

        view = await use_case.for_episode(SERIES_ID.value, 201)

        assert view.based_on_comment_count == 1

    async def test_an_episode_comment_changes_the_baseline(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
        clock: FixedClock,
    ) -> None:
        provider = ScriptedInsightProvider(answers=("one",))
        use_case = build(gateway, unit_of_work, provider, clock)

        await unit_of_work.comments.add(
            Comment(
                id="e1",
                viewer_id=ViewerId(VIEWER),
                target=ContentTarget.EPISODE,
                series_id=SERIES_ID,
                episode_id=EpisodeId(201),
                text=CommentText("episode specific"),
                created_at=MOMENT,
            )
        )
        view = await use_case.for_episode(SERIES_ID.value, 201)

        assert view.based_on_comment_count == 1


def test_the_store_is_empty_in_a_fresh_fake(unit_of_work: InMemoryUnitOfWork) -> None:
    assert unit_of_work.insights.rows == {}


def test_a_stored_insight_is_immutable() -> None:
    stored = StoredInsight(
        target=ContentTarget.SERIES,
        target_id=1,
        text="x",
        provider="heuristic",
        degraded=True,
        based_on_comment_count=0,
        generated_at=MOMENT,
    )
    with pytest.raises(AttributeError):
        stored.text = "y"  # type: ignore[misc]
