"""Level 1: the stored insight and the freshness rule agreed with the client.

The rule is the cost-control mechanism of the AI feature: an insight is reused
until a given number of new comments exist. It is pure logic, so it belongs in the
domain and is tested without a database.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import ContentTarget

NOW = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)


def insight(
    *,
    based_on: int = 3,
    text: str = "A curated insight.",
    provider: str = "huggingface",
    target: ContentTarget = ContentTarget.SERIES,
    target_id: int = 169,
) -> StoredInsight:
    return StoredInsight(
        target=target,
        target_id=target_id,
        text=text,
        provider=provider,
        degraded=False,
        based_on_comment_count=based_on,
        generated_at=NOW,
    )


class TestFreshness:
    def test_it_is_fresh_while_no_new_comment_arrives(self) -> None:
        assert insight(based_on=3).is_fresh_for(3) is True

    def test_a_single_new_comment_invalidates_it(self) -> None:
        # The client's call: "as a simple test, consider 1 comment is enough".
        assert insight(based_on=3).is_fresh_for(4) is False

    def test_two_new_comments_invalidate_it_by_default(self) -> None:
        assert insight(based_on=3).is_fresh_for(5) is False

    def test_the_threshold_is_configurable(self) -> None:
        stored = insight(based_on=3)

        assert stored.is_fresh_for(4, threshold=2) is True
        assert stored.is_fresh_for(5, threshold=2) is False

    def test_a_zero_threshold_means_always_regenerate(self) -> None:
        # 0 is the default: reuse is disabled and every request hits the provider,
        # even when nothing about the input changed.
        stored = insight(based_on=3)

        assert stored.is_fresh_for(3, threshold=0) is False
        assert stored.is_fresh_for(4, threshold=0) is False

    def test_a_negative_threshold_is_treated_as_disabled(self) -> None:
        assert insight(based_on=3).is_fresh_for(3, threshold=-5) is False

    def test_a_lower_count_is_never_considered_fresh(self) -> None:
        # Defensive: only reachable if comments were deleted out of band.
        assert insight(based_on=5).is_fresh_for(2) is False

    def test_an_insight_built_from_zero_comments_is_fresh_until_the_first_one(self) -> None:
        stored = insight(based_on=0)

        assert stored.is_fresh_for(0) is True
        assert stored.is_fresh_for(1) is False


class TestInvariants:
    def test_text_is_required(self) -> None:
        with pytest.raises(InvalidValue):
            insight(text="   ")

    def test_provider_is_required(self) -> None:
        with pytest.raises(InvalidValue):
            insight(provider="  ")

    def test_the_subject_must_be_identifiable(self) -> None:
        with pytest.raises(InvalidValue):
            insight(target_id=0)

    def test_the_baseline_cannot_be_negative(self) -> None:
        with pytest.raises(InvalidValue):
            insight(based_on=-1)

    def test_the_timestamp_must_be_timezone_aware(self) -> None:
        with pytest.raises(InvalidValue):
            StoredInsight(
                target=ContentTarget.SERIES,
                target_id=1,
                text="x",
                provider="heuristic",
                degraded=True,
                based_on_comment_count=0,
                generated_at=datetime(2024, 1, 1, 12, 0),
            )


def test_a_series_and_an_episode_insight_are_distinct_subjects() -> None:
    series = insight(target=ContentTarget.SERIES, target_id=1)
    episode = insight(target=ContentTarget.EPISODE, target_id=1)

    assert (series.target, series.target_id) != (episode.target, episode.target_id)
