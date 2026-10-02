"""Deterministic, offline **heuristic** provider — the last tier of the chain.

The client's guidance for the fallback strategy was explicit: *"the idea is to
create a heuristic process"* rather than paying for a second model (see
``docs/CLIENT-FEEDBACK.md``). This provider is that process:

* it never fails and needs no credentials, so an insight is always produced;
* it derives the text from data we already hold — genres, the summary and the
  community comments — with a small, readable and testable set of rules;
* it is **honest**: the result is flagged ``degraded`` and tagged ``heuristic``,
  so neither the API consumer nor the UI can mistake it for a model's output.
"""

from __future__ import annotations

import re
from collections import Counter

from tv_insight.application.ports.insight import (
    InsightProvider,
    InsightRequest,
    InsightResult,
)
from tv_insight.domain.services.insight_prompt import InsightSubject
from tv_insight.domain.text import truncate

MAX_WORDS = 60
SUMMARY_CHARS = 190
MAX_COMMENT_WORDS = 12

_AUDIENCE_BY_GENRE = {
    "drama": "viewers who like character-driven storytelling",
    "comedy": "anyone after something light between heavier shows",
    "science-fiction": "fans of speculative worlds and big ideas",
    "fantasy": "viewers who enjoy mythology and world building",
    "thriller": "people who like tension and slow reveals",
    "horror": "an audience that enjoys dread over jump scares",
    "crime": "fans of investigations and moral grey areas",
    "mystery": "viewers who like piecing clues together",
    "romance": "people looking for emotional, relationship-led plots",
    "action": "viewers who want momentum and set pieces",
    "anime": "fans of stylised animation and long arcs",
    "adventure": "viewers who enjoy journeys and discovery",
    "documentary": "people curious about the real world",
    "family": "a household audience looking for something to share",
    "war": "viewers drawn to conflict and its human cost",
    "history": "people who enjoy period settings and real events",
}

# Words that carry no signal when we look for recurring themes. Kept as short
# lines so no source line becomes unwieldy; ``split()`` does the rest.
_STOPWORD_TEXT = """
a about after again all also am an and any are as at be because been before
being but by can could did do does doing down during each few for from further
had has have having he her here hers him his how i if in into is it its just me
more most my no nor not of off on once only or other our out over own same she
should so some such than that the their them then there these they this those
through to too under until up very was we were what when where which while who
whom why will with would you your yours
de da do das dos em um uma para com que nao mais muito serie series episodio
temporada
"""

_STOPWORDS = frozenset(_STOPWORD_TEXT.split())


class HeuristicInsightProvider(InsightProvider):
    """Composes a short paragraph from the structured subject, without an LLM."""

    @property
    def name(self) -> str:
        return "heuristic"

    def is_available(self) -> bool:
        return True

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        del refresh
        return InsightResult(
            text=self._compose(request.subject),
            provider=self.name,
            degraded=True,
            notes=(
                "Heuristic fallback: composed offline from the summary, genres and "
                "community comments.",
            ),
        )

    # ------------------------------------------------------------------ rules

    def _compose(self, subject: InsightSubject) -> str:
        genres = list(subject.genres) or ["drama"]
        sentences = [self._opener(subject, genres)]

        summary = truncate(subject.summary.strip(), SUMMARY_CHARS)
        if summary:
            sentences.append(_sentence(summary))

        community = self._community_sentence(subject.comments)
        if community:
            sentences.append(community)

        sentences.append(f"It should appeal to {self._audience(genres[0])}.")
        return _limit_words(" ".join(sentences), MAX_WORDS)

    @staticmethod
    def _opener(subject: InsightSubject, genres: list[str]) -> str:
        if subject.is_episode:
            where = f'"{subject.title}"'
            if subject.series_name:
                where += f" from {subject.series_name}"
            if subject.episode_code:
                where += f" ({subject.episode_code})"
            return f"{where} is an episode built around {_join(genres)}."
        return f'"{subject.title}" is a series built around {_join(genres)}.'

    @staticmethod
    def _community_sentence(comments: tuple[str, ...]) -> str:
        relevant = [comment for comment in comments if comment.strip()]
        if not relevant:
            return ""
        themes = _recurring_themes(relevant)
        if themes:
            listed = ", ".join(f'"{theme}"' for theme in themes)
            return f"{len(relevant)} community comments keep returning to {listed}."
        lead = " ".join(relevant[0].split()[:MAX_COMMENT_WORDS]).rstrip(" .,;:")
        return f'{len(relevant)} community comments so far, for instance "{lead}".'

    @staticmethod
    def _audience(primary_genre: str) -> str:
        return _AUDIENCE_BY_GENRE.get(primary_genre.lower(), f"fans of {primary_genre.lower()}")


def _recurring_themes(comments: list[str], limit: int = 2) -> list[str]:
    """Words that appear in more than one comment, most frequent first.

    A deliberately crude heuristic: it is a fallback, and "returns to X" is a
    claim we only make when the word really repeats.
    """
    occurrences: Counter[str] = Counter()
    for comment in comments:
        seen = {
            word
            for word in re.findall(r"[a-zà-ÿ]{4,}", comment.lower())
            if word not in _STOPWORDS
        }
        occurrences.update(seen)
    repeated = [(word, count) for word, count in occurrences.most_common() if count > 1]
    return [word for word, _ in repeated[:limit]]


def _join(genres: list[str]) -> str:
    if len(genres) == 1:
        return genres[0].lower()
    if len(genres) == 2:
        return f"{genres[0].lower()} and {genres[1].lower()}"
    return f"{genres[0].lower()}, {genres[1].lower()} and {genres[2].lower()}"


def _sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _limit_words(text: str, limit: int) -> str:
    words = text.split()
    if len(words) <= limit:
        return text
    return " ".join(words[:limit]).rstrip(",;:") + "."
