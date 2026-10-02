"""Response models.

The API contract is declared here, independently from the use case DTOs: the
frontend can stay stable while the application layer evolves. These are the only
classes FastAPI serialises.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SeriesCardModel(ApiModel):
    id: int
    name: str
    year: int | None = None
    poster_url: str | None = None
    poster_thumbnail_url: str | None = None
    genres: list[str] = Field(default_factory=list)
    status: str | None = None
    rating: float | None = None
    network: str | None = None
    language: str | None = None


class EpisodeModel(ApiModel):
    id: int
    name: str
    season: int
    number: int
    code: str
    summary: str
    airdate: date | None = None
    runtime_minutes: int | None = None
    image_url: str | None = None
    watched: bool = False


class SeasonModel(ApiModel):
    number: int
    label: str
    episodes: list[EpisodeModel] = Field(default_factory=list)
    watched: int = 0
    total: int = 0
    progress: float = 0.0


class CommentModel(ApiModel):
    id: str
    target: str
    series_id: int
    text: str
    created_at: datetime
    episode_id: int | None = None
    episode_code: str | None = None
    author: str = "Anonymous viewer"
    mine: bool = False


class SearchResponse(ApiModel):
    query: str
    count: int
    results: list[SeriesCardModel] = Field(default_factory=list)


class SeriesDetailModel(ApiModel):
    series: SeriesCardModel
    summary: str
    seasons: list[SeasonModel] = Field(default_factory=list)
    watched: int = 0
    total_episodes: int = 0
    progress: float = 0.0
    comment_count: int = 0
    comments: list[CommentModel] = Field(default_factory=list)


class EpisodeDetailModel(ApiModel):
    series: SeriesCardModel
    episode: EpisodeModel
    comment_count: int = 0
    comments: list[CommentModel] = Field(default_factory=list)
    next_episode: EpisodeModel | None = None


class InsightsResponse(ApiModel):
    text: str
    provider: str
    degraded: bool = False
    cached: bool = False
    generated_at: datetime | None = None
    target: str = "series"
    target_id: int = 0
    based_on_comment_count: int = 0
    notes: list[str] = Field(default_factory=list)


class CommentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    episode_id: int | None = Field(default=None, gt=0)


class WatchRequest(BaseModel):
    watched: bool = True


class ProviderStatus(ApiModel):
    provider: str
    available: bool
    model: str | None = None


class HealthModel(ApiModel):
    status: str
    version: str
    database: str
    insights: list[ProviderStatus] = Field(default_factory=list)


class ErrorModel(ApiModel):
    error: str
    detail: str | None = None
