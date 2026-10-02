"""Composition root.

The single place that knows every concrete class and wires them together. Reading
this file top to bottom is reading the dependency graph of the application, and
nothing else in the codebase needs to import two layers at once.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine

from tv_insight.application.ports.clock import Clock, SystemClock
from tv_insight.application.ports.insight import InsightProvider
from tv_insight.application.ports.persistence import UnitOfWork
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.application.use_cases.add_comment import AddComment
from tv_insight.application.use_cases.generate_insight import GenerateInsight
from tv_insight.application.use_cases.get_episode_detail import GetEpisodeDetail
from tv_insight.application.use_cases.get_series_details import GetSeriesDetails
from tv_insight.application.use_cases.list_comments import ListComments
from tv_insight.application.use_cases.search_series import SearchSeries
from tv_insight.application.use_cases.set_episode_watched import SetEpisodeWatched
from tv_insight.domain.services.insight_prompt import InsightPromptComposer
from tv_insight.domain.services.watch_progress import WatchProgressService
from tv_insight.infrastructure.ai.factory import build_insight_provider
from tv_insight.infrastructure.cache import AsyncTtlCache
from tv_insight.infrastructure.config import Settings
from tv_insight.infrastructure.db.session import create_engine, create_session_factory, ping
from tv_insight.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tv_insight.infrastructure.tvmaze.caching import CachingTvMazeGateway
from tv_insight.infrastructure.tvmaze.client import HttpTvMazeGateway

HTTP_TIMEOUT_SLACK = 5.0


@dataclass(slots=True)
class Container:
    """Wired object graph for one application instance."""

    settings: Settings
    engine: AsyncEngine
    http_client: httpx.AsyncClient
    gateway: TvMazeGateway
    insight_provider: InsightProvider
    unit_of_work: Callable[[], UnitOfWork]
    database_health: Callable[[], Awaitable[bool]] | None = None
    clock: Clock = field(default_factory=SystemClock)
    progress_service: WatchProgressService = field(default_factory=WatchProgressService)
    prompt_composer: InsightPromptComposer = field(default_factory=InsightPromptComposer)
    search_series: SearchSeries = field(init=False)
    get_series_details: GetSeriesDetails = field(init=False)
    get_episode_detail: GetEpisodeDetail = field(init=False)
    set_episode_watched: SetEpisodeWatched = field(init=False)
    add_comment: AddComment = field(init=False)
    list_comments: ListComments = field(init=False)
    generate_insight: GenerateInsight = field(init=False)

    def __post_init__(self) -> None:
        if self.database_health is None:
            self.database_health = lambda: ping(self.engine)
        self.search_series = SearchSeries(self.gateway)
        self.get_series_details = GetSeriesDetails(
            self.gateway, self.unit_of_work, self.progress_service
        )
        self.get_episode_detail = GetEpisodeDetail(self.gateway, self.unit_of_work)
        self.set_episode_watched = SetEpisodeWatched(
            self.gateway, self.unit_of_work, self.clock
        )
        self.add_comment = AddComment(self.gateway, self.unit_of_work, self.clock)
        self.list_comments = ListComments(self.gateway, self.unit_of_work)
        self.generate_insight = GenerateInsight(
            self.gateway,
            self.unit_of_work,
            self.insight_provider,
            self.prompt_composer,
            self.clock,
            max_comments=self.settings.ai_max_comments,
            comment_threshold=self.settings.ai_insight_comment_threshold,
        )

    @classmethod
    def build(cls, settings: Settings) -> Container:
        engine = create_engine(settings)
        session_factory = create_session_factory(engine)

        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                settings.tvmaze_timeout_seconds + HTTP_TIMEOUT_SLACK,
                connect=settings.tvmaze_timeout_seconds,
            ),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            headers={"User-Agent": "tv-insight/1.0"},
        )

        gateway: TvMazeGateway = CachingTvMazeGateway(
            HttpTvMazeGateway(
                base_url=settings.tvmaze_base_url,
                timeout_seconds=settings.tvmaze_timeout_seconds,
                max_retries=settings.tvmaze_max_retries,
                client=http_client,
            ),
            AsyncTtlCache(ttl_seconds=settings.tvmaze_cache_ttl_seconds),
        )

        return cls(
            settings=settings,
            engine=engine,
            http_client=http_client,
            gateway=gateway,
            insight_provider=build_insight_provider(settings, http_client),
            unit_of_work=lambda: SqlAlchemyUnitOfWork(session_factory),
            prompt_composer=InsightPromptComposer(
                max_summary_chars=settings.ai_max_summary_chars,
                max_comments=settings.ai_max_comments,
            ),
        )

    async def shutdown(self) -> None:
        await self.gateway.aclose()
        await self.http_client.aclose()
        await self.engine.dispose()
