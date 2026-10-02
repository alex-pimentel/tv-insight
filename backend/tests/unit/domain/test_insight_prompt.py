"""Level 1: prompt composition rules live in the domain."""

from __future__ import annotations

from tv_insight.domain.services.insight_prompt import (
    SYSTEM_INSTRUCTION,
    InsightPromptComposer,
    InsightSubject,
)
from tv_insight.domain.value_objects import ContentTarget


def _subject(**overrides: object) -> InsightSubject:
    base = {
        "target": ContentTarget.SERIES,
        "title": "Breaking Bad",
        "summary": "A chemistry teacher turns to crime.",
        "genres": ("Drama", "Crime"),
        "comments": ("Best show ever",),
    }
    base.update(overrides)
    return InsightSubject(**base)  # type: ignore[arg-type]


def test_prompt_carries_system_instruction() -> None:
    prompt = InsightPromptComposer().compose(_subject())
    assert prompt.system == SYSTEM_INSTRUCTION


def test_prompt_includes_every_domain_input() -> None:
    prompt = InsightPromptComposer().compose(_subject())
    user = prompt.user

    assert "Title: Breaking Bad" in user
    assert "Summary: A chemistry teacher turns to crime." in user
    assert "Genres: Drama, Crime" in user
    assert "- Best show ever" in user
    assert "Target: series" in user


def test_episode_context_is_added() -> None:
    prompt = InsightPromptComposer().compose(
        _subject(
            target=ContentTarget.EPISODE,
            title="Grilled",
            series_name="Breaking Bad",
            episode_code="S02E02",
        )
    )
    assert "Target: episode" in prompt.user
    assert "Series: Breaking Bad" in prompt.user
    assert "Episode: S02E02" in prompt.user


def test_series_name_is_not_duplicated_in_title() -> None:
    prompt = InsightPromptComposer().compose(
        _subject(series_name="Breaking Bad")
    )
    assert "Series:" not in prompt.user


def test_comments_are_capped() -> None:
    composer = InsightPromptComposer(max_comments=2)
    subject = _subject(comments=("one", "two", "three", "four"))

    prompt = composer.compose(subject)

    assert "- one" in prompt.user
    assert "- two" in prompt.user
    assert "- three" not in prompt.user


def test_long_summary_is_truncated() -> None:
    composer = InsightPromptComposer(max_summary_chars=40)
    prompt = composer.compose(_subject(summary="word " * 100))

    summary_line = next(
        line for line in prompt.user.splitlines() if line.startswith("Summary:")
    )
    assert len(summary_line) <= 60


def test_missing_inputs_are_reported_as_unknown() -> None:
    prompt = InsightPromptComposer().compose(
        _subject(summary="", genres=(), comments=())
    )
    assert "Summary: not available" in prompt.user
    assert "Genres: unknown" in prompt.user
    assert "Viewer comments: none yet" in prompt.user


def test_is_episode_flag() -> None:
    assert _subject(target=ContentTarget.EPISODE).is_episode is True
    assert _subject().is_episode is False
