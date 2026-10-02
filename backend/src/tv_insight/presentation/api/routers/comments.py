"""Comment endpoints.

One resource for both targets: ``episode_id`` in the query string or the body
decides whether the comment hangs off the series or off an episode.
"""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from tv_insight.presentation.api.dependencies import ContainerDep, ViewerIdDep
from tv_insight.presentation.api.responses import ERROR_RESPONSES
from tv_insight.presentation.api.schemas import CommentModel, CommentRequest

router = APIRouter(
    prefix="/series/{series_id}/comments",
    tags=["comments"],
    responses=ERROR_RESPONSES,
)


@router.get("", response_model=list[CommentModel], summary="List comments")
async def list_comments(
    container: ContainerDep,
    viewer_id: ViewerIdDep,
    series_id: int,
    episode_id: int | None = Query(default=None, gt=0),
) -> list[CommentModel]:
    comments = await container.list_comments.execute(
        series_id=series_id, viewer_id=viewer_id, episode_id=episode_id
    )
    return [CommentModel.model_validate(comment) for comment in comments]


@router.post(
    "",
    response_model=CommentModel,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment",
)
async def add_comment(
    container: ContainerDep,
    viewer_id: ViewerIdDep,
    series_id: int,
    payload: CommentRequest,
) -> CommentModel:
    comment = await container.add_comment.execute(
        series_id=series_id,
        viewer_id=viewer_id,
        text=payload.text,
        episode_id=payload.episode_id,
    )
    return CommentModel.model_validate(comment)
