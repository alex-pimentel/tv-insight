"""Domain -> DTO mapping.

Mapping lives here (and not inside the use cases) so the orchestration code reads
as a sequence of business steps. Presentation does the final DTO -> response model
step, which keeps the API contract free to diverge from the use case output.
"""

from __future__ import annotations

from tv_insight.application.dto import CommentView, EpisodeView, SeriesCard
from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.series import Series
from tv_insight.domain.value_objects import EpisodeId, ViewerId


def series_to_card(series: Series) -> SeriesCard:
    return SeriesCard(
        id=series.id.value,
        name=series.name,
        year=series.year,
        poster_url=series.poster_url,
        poster_thumbnail_url=series.poster_thumbnail_url,
        genres=series.genre_names,
        status=series.status,
        rating=float(series.rating) if series.rating else None,
        network=series.network,
        language=series.language,
    )


def episode_to_view(episode: Episode, *, watched: bool) -> EpisodeView:
    return EpisodeView(
        id=episode.id.value,
        name=episode.name,
        season=episode.season.value,
        number=episode.number.value,
        code=episode.code,
        summary=episode.synopsis(),
        airdate=episode.airdate,
        runtime_minutes=episode.runtime_minutes,
        image_url=episode.image_url,
        watched=watched,
    )


def comment_to_view(
    comment: Comment,
    *,
    viewer_id: ViewerId,
    episode_codes: dict[EpisodeId, str] | None = None,
) -> CommentView:
    code = None
    if comment.episode_id is not None and episode_codes:
        code = episode_codes.get(comment.episode_id)
    return CommentView(
        id=comment.id,
        target=comment.target.value,
        series_id=comment.series_id.value,
        episode_id=comment.episode_id.value if comment.episode_id else None,
        episode_code=code,
        text=comment.text.value,
        created_at=comment.created_at,
        mine=comment.viewer_id == viewer_id,
    )
