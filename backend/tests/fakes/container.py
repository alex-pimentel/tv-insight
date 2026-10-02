"""Builds a fully wired ``Container`` backed by test doubles.

This is what makes the integration suite honest *and* fast: the same object graph
the application uses in production, with the three external boundaries (catalogue,
database, LLM) replaced by in-memory fakes.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncEngine

from tests.fakes import (
    FixedClock,
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
    RecordingInsightProvider,
    ScriptedInsightProvider,
)
from tv_insight.infrastructure.composition import Container
from tv_insight.infrastructure.config import Settings


def build_test_container(
    *,
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    provider: Any | None = None,
    clock: FixedClock | None = None,
    database_ok: bool = True,
    settings: Settings | None = None,
) -> Container:
    async def database_health() -> bool:
        return database_ok

    return Container(
        settings=settings or Settings(app_env="test", ai_provider_order="heuristic"),
        engine=cast("AsyncEngine", object()),
        http_client=cast(Any, object()),
        gateway=gateway,
        insight_provider=provider or RecordingInsightProvider(),
        unit_of_work=lambda: unit_of_work,
        database_health=database_health,
        clock=clock or FixedClock(),
    )


def default_provider(
    answers: Sequence[str] = ("A curated insight about the show.",),
) -> ScriptedInsightProvider:
    return ScriptedInsightProvider(name="test-provider", answers=answers)
