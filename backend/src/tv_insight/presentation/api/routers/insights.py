"""AI insight endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tv_insight.presentation.api.dependencies import ContainerDep
from tv_insight.presentation.api.schemas import InsightsResponse

router = APIRouter(prefix="/series/{series_id}", tags=["insights"])


@router.get("/insight", response_model=InsightsResponse, summary="Insight for a series")
async def series_insight(
    container: ContainerDep,
    series_id: int,
    refresh: bool = Query(default=False, description="Bypass the insight cache"),
) -> InsightsResponse:
    insight = await container.generate_insight.for_series(series_id, refresh=refresh)
    return InsightsResponse.model_validate(insight)


@router.get(
    "/episodes/{episode_id}/insight",
    response_model=InsightsResponse,
    summary="Insight for an episode",
)
async def episode_insight(
    container: ContainerDep,
    series_id: int,
    episode_id: int,
    refresh: bool = Query(default=False, description="Bypass the insight cache"),
) -> InsightsResponse:
    insight = await container.generate_insight.for_episode(
        series_id, episode_id, refresh=refresh
    )
    return InsightsResponse.model_validate(insight)
