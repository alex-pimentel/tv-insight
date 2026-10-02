"""Episode detail and watched-tracking endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from tv_insight.presentation.api.dependencies import ContainerDep, ViewerIdDep
from tv_insight.presentation.api.schemas import (
    EpisodeDetailModel,
    EpisodeModel,
    WatchRequest,
)

router = APIRouter(prefix="/series/{series_id}/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeDetailModel, summary="Episode details")
async def get_episode_detail(
    container: ContainerDep,
    viewer_id: ViewerIdDep,
    series_id: int,
    episode_id: int,
) -> EpisodeDetailModel:
    detail = await container.get_episode_detail.execute(series_id, episode_id, viewer_id)
    return EpisodeDetailModel.model_validate(detail)


@router.put("/{episode_id}/watched", response_model=EpisodeModel, summary="Mark episode")
async def set_episode_watched(
    container: ContainerDep,
    viewer_id: ViewerIdDep,
    series_id: int,
    episode_id: int,
    payload: WatchRequest,
) -> EpisodeModel:
    episode = await container.set_episode_watched.execute(
        series_id, episode_id, viewer_id, watched=payload.watched
    )
    return EpisodeModel.model_validate(episode)
