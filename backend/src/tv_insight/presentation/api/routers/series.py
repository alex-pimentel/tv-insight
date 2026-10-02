"""Series search and detail endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from tv_insight.presentation.api.dependencies import ContainerDep, ViewerIdDep
from tv_insight.presentation.api.schemas import (
    SearchResponse,
    SeriesCardModel,
    SeriesDetailModel,
)

router = APIRouter(prefix="/series", tags=["series"])


@router.get("/search", response_model=SearchResponse, summary="Search TV series")
async def search_series(
    container: ContainerDep,
    q: str = Query(min_length=1, max_length=100, description="Free text query"),
) -> SearchResponse:
    results = await container.search_series.execute(q)
    return SearchResponse(
        query=q,
        count=len(results),
        results=[SeriesCardModel.model_validate(item) for item in results],
    )


@router.get("/{series_id}", response_model=SeriesDetailModel, summary="Series details")
async def get_series_detail(
    container: ContainerDep,
    viewer_id: ViewerIdDep,
    series_id: int,
) -> SeriesDetailModel:
    detail = await container.get_series_details.execute(series_id, viewer_id)
    return SeriesDetailModel.model_validate(detail)
