"""Use case: generate an insight for a series or an episode.

The behaviour is a small, explicit decision matrix agreed with the team:

    1. **Every explicit request tries the model providers first.** Clicking "View
       insights" always attempts a fresh generation, so the answer is current.
    2. **If the providers fail and a stored insight exists, serve the stored one.**
       The store only ever holds answers produced by a real model, so it is the
       "last known good" answer - worth more than a synthetic fallback.
    3. **If the providers fail and the store is empty, use the heuristic tier.**
       The feature still answers, flagged as degraded.

Cost control (reusing an insight until N new comments exist) is still available
through ``comment_threshold``; ``0`` - the default - disables reuse and implements
rule 1. The in-process provider cache is likewise off by default, so "generate"
really means "call the provider".

The use case still contains no AI knowledge: it assembles the *subject*, asks the
domain service for a prompt, and hands it to whichever provider the composition
root wired in.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from tv_insight.application.dto import InsightView
from tv_insight.application.errors import ProviderUnavailable, translated_domain_errors
from tv_insight.application.ports.clock import Clock
from tv_insight.application.ports.insight import (
    InsightProvider,
    InsightRequest,
    InsightResult,
)
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.services.insight_prompt import (
    InsightPromptComposer,
    InsightSubject,
)
from tv_insight.domain.text import to_plain_text
from tv_insight.domain.value_objects import ContentTarget, EpisodeId, SeriesId

DEFAULT_MAX_COMMENTS = 12
#: 0 = regenerate on every request (the default). A positive value restores the
#: cost-control rule "reuse until N new comments exist".
DEFAULT_COMMENT_THRESHOLD = 0


class GenerateInsight:
    """Produces a short, curated paragraph about a series or an episode."""

    def __init__(
        self,
        gateway: TvMazeGateway,
        unit_of_work: Callable[[], UnitOfWork],
        provider: InsightProvider,
        composer: InsightPromptComposer,
        clock: Clock,
        max_comments: int = DEFAULT_MAX_COMMENTS,
        comment_threshold: int = DEFAULT_COMMENT_THRESHOLD,
    ) -> None:
        self._gateway = gateway
        self._uow_factory = unit_of_work
        self._provider = provider
        self._composer = composer
        self._clock = clock
        self._max_comments = max_comments
        self._comment_threshold = max(comment_threshold, 0)

    # ------------------------------------------------------------------ public

    async def for_series(self, series_id: int, *, refresh: bool = False) -> InsightView:
        with translated_domain_errors():
            identifier = SeriesId(series_id)

        series = await self._gateway.get_series(identifier)

        async with self._uow_factory() as uow:
            current_count = await uow.comments.count_for_series(identifier)
            stored = await uow.insights.get(ContentTarget.SERIES, identifier.value)
            reusable = self._reusable(stored, current_count, refresh)
            if reusable is not None:
                return self._from_store(reusable)
            comments = await uow.comments.list_for_series(identifier, limit=self._max_comments)

        subject = InsightSubject(
            target=ContentTarget.SERIES,
            title=series.name,
            summary=to_plain_text(series.summary),
            genres=series.genre_names,
            comments=tuple(comment.text.value for comment in comments),
        )
        return await self._generate(
            subject,
            target=ContentTarget.SERIES,
            target_id=series.id.value,
            based_on=current_count,
            stale=stored,
            refresh=refresh,
        )

    async def for_episode(
        self, series_id: int, episode_id: int, *, refresh: bool = False
    ) -> InsightView:
        with translated_domain_errors():
            series_identifier = SeriesId(series_id)
            episode_identifier = EpisodeId(episode_id)

        series = await self._gateway.get_series(series_identifier)
        guide = await self._gateway.get_episodes(series_identifier)
        with translated_domain_errors():
            episode = guide.find(episode_identifier)

        async with self._uow_factory() as uow:
            episode_count = await uow.comments.count_for_episode(episode_identifier)
            # With no episode comments yet we feed the series conversation, so the
            # baseline must be the count of whatever we actually fed.
            if episode_count > 0:
                current_count = episode_count
            else:
                current_count = await uow.comments.count_for_series(series_identifier)

            stored = await uow.insights.get(ContentTarget.EPISODE, episode.id.value)
            reusable = self._reusable(stored, current_count, refresh)
            if reusable is not None:
                return self._from_store(reusable)

            if episode_count > 0:
                comments = await uow.comments.list_for_episode(
                    episode_identifier, limit=self._max_comments
                )
            else:
                comments = await uow.comments.list_for_series(
                    series_identifier, limit=self._max_comments
                )

        subject = InsightSubject(
            target=ContentTarget.EPISODE,
            title=episode.name,
            series_name=series.name,
            episode_code=episode.code,
            summary=to_plain_text(episode.summary),
            genres=series.genre_names,
            comments=tuple(comment.text.value for comment in comments),
        )
        return await self._generate(
            subject,
            target=ContentTarget.EPISODE,
            target_id=episode.id.value,
            based_on=current_count,
            stale=stored,
            refresh=refresh,
        )

    # --------------------------------------------------------------- internals

    def _reusable(
        self, stored: StoredInsight | None, current_count: int, refresh: bool
    ) -> StoredInsight | None:
        """Return the stored insight when reuse is enabled and still valid.

        With the default threshold of ``0`` this is always ``None``: every request
        generates. It exists so the cost-control window stays one setting away
        rather than requiring a code change.
        """
        if stored is None or refresh:
            return None
        if stored.is_fresh_for(current_count, threshold=self._comment_threshold):
            return stored
        return None

    async def _generate(
        self,
        subject: InsightSubject,
        *,
        target: ContentTarget,
        target_id: int,
        based_on: int,
        stale: StoredInsight | None,
        refresh: bool,
    ) -> InsightView:
        request = InsightRequest(prompt=self._composer.compose(subject), subject=subject)

        try:
            result = await self._provider.generate(request, refresh=refresh)
        except ProviderUnavailable:
            # Only reachable if every tier - including the terminal heuristic -
            # failed. Last resort: the stored answer, which beats an error.
            return self._stored_or_raise(stale, "Generation failed")

        text = result.text.strip()
        if not text:
            return self._stored_or_raise(stale, "The provider returned nothing")

        if result.degraded and stale is not None:
            # The chain fell through to the local heuristic. A previous answer from
            # a real model is worth more than a freshly composed one, and the store
            # only ever holds model answers.
            return self._from_store_with_note(
                stale, "Model providers unavailable; serving the last stored insight."
            )

        generated_at = self._clock.now()
        if not result.degraded:
            # Persist only model answers, so the stored insight is always the last
            # known good one and can never be overwritten by a heuristic.
            await self._persist(
                target=target,
                target_id=target_id,
                text=text,
                result=result,
                based_on=based_on,
                generated_at=generated_at,
            )

        return InsightView(
            text=text,
            provider=result.provider,
            degraded=result.degraded,
            cached=False,
            generated_at=generated_at,
            target=target.value,
            target_id=target_id,
            based_on_comment_count=based_on,
            notes=result.notes,
        )

    async def _persist(
        self,
        *,
        target: ContentTarget,
        target_id: int,
        text: str,
        result: InsightResult,
        based_on: int,
        generated_at: datetime,
    ) -> None:
        stored = StoredInsight(
            target=target,
            target_id=target_id,
            text=text,
            provider=result.provider,
            degraded=result.degraded,
            based_on_comment_count=based_on,
            generated_at=generated_at,
        )

        async with self._uow_factory() as uow:
            await uow.insights.save(stored)
            await uow.commit()

    def _stored_or_raise(self, stale: StoredInsight | None, reason: str) -> InsightView:
        if stale is not None:
            return self._from_store_with_note(
                stale, f"{reason}; serving the last stored insight."
            )
        raise ProviderUnavailable(f"{reason} and there is no stored insight to fall back on")

    def _from_store(self, stored: StoredInsight) -> InsightView:
        return InsightView(
            text=stored.text,
            provider=stored.provider,
            degraded=stored.degraded,
            cached=True,
            generated_at=stored.generated_at,
            target=stored.target.value,
            target_id=stored.target_id,
            based_on_comment_count=stored.based_on_comment_count,
            notes=("Served from the stored insight; no provider was called.",),
        )

    def _from_store_with_note(self, stored: StoredInsight, note: str) -> InsightView:
        return replace(self._from_store(stored), degraded=True, notes=(note,))
