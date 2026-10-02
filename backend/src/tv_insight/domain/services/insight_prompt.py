"""Domain service that turns catalogue data into an LLM prompt.

Why is this a *domain* service and not an infrastructure detail? Because the
business rule "an insight is derived from the summary, the genres and the user
comments, and must stay short" belongs to the domain. The provider (HuggingFace,
OpenRouter, ...) is an implementation detail behind a port.
"""

from __future__ import annotations

from dataclasses import dataclass

from tv_insight.domain.text import truncate
from tv_insight.domain.value_objects import ContentTarget

SYSTEM_INSTRUCTION = (
    "You are a concise TV series curator. You write a single short paragraph "
    "(2 to 3 sentences, at most 60 words) describing what a viewer will find in "
    "the given series or episode, and which audience it appeals to. "
    "Base yourself strictly on the provided summary, genres and viewer comments. "
    "Never invent plot details. Answer with plain prose, no markdown, no lists, "
    "no preamble."
)


@dataclass(frozen=True, slots=True)
class InsightSubject:
    """Everything the domain allows an insight to be based on."""

    target: ContentTarget
    title: str
    summary: str
    genres: tuple[str, ...] = ()
    comments: tuple[str, ...] = ()
    series_name: str | None = None
    episode_code: str | None = None

    @property
    def is_episode(self) -> bool:
        return self.target is ContentTarget.EPISODE


@dataclass(frozen=True, slots=True)
class InsightPrompt:
    """Provider agnostic prompt. Adapters translate it to their own payload."""

    system: str
    user: str


class InsightPromptComposer:
    """Builds the prompt, enforcing the size limits as an invariant."""

    def __init__(self, max_summary_chars: int = 1200, max_comments: int = 12) -> None:
        self._max_summary_chars = max_summary_chars
        self._max_comments = max_comments

    def compose(self, subject: InsightSubject) -> InsightPrompt:
        return InsightPrompt(system=SYSTEM_INSTRUCTION, user=self._user_message(subject))

    def _user_message(self, subject: InsightSubject) -> str:
        lines: list[str] = [f"Target: {subject.target.value}", f"Title: {subject.title}"]

        if subject.series_name and subject.series_name != subject.title:
            lines.append(f"Series: {subject.series_name}")
        if subject.episode_code:
            lines.append(f"Episode: {subject.episode_code}")

        summary = subject.summary.strip() or "not available"
        lines.append(f"Summary: {truncate(summary, self._max_summary_chars)}")
        lines.append(f"Genres: {', '.join(subject.genres) if subject.genres else 'unknown'}")

        comments = [c.strip() for c in subject.comments if c.strip()][: self._max_comments]
        if comments:
            lines.append("Viewer comments:")
            lines.extend(f"- {truncate(comment, 240)}" for comment in comments)
        else:
            lines.append("Viewer comments: none yet")

        lines.append(
            "Write the insight now, in English, as a single short paragraph."
        )
        return "\n".join(lines)
