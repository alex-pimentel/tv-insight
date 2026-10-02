"""HTTP adapter for the TVMaze public catalogue."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from typing import Any

import httpx

from tv_insight.application.errors import ExternalServiceError, ResourceNotFound
from tv_insight.application.ports.tvmaze import TvMazeGateway
from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.entities.series import Series
from tv_insight.domain.exceptions import InvalidValue
from tv_insight.domain.value_objects import SearchTerm, SeriesId
from tv_insight.infrastructure.logging import get_logger
from tv_insight.infrastructure.resilience import retrying_call
from tv_insight.infrastructure.tvmaze.mappers import to_episode, to_series

logger = get_logger(__name__)

USER_AGENT = "tv-insight/1.0 (+architecture-technical-assignment)"


def _is_json_array(value: Any) -> bool:
    """True for a JSON array, and deliberately False for a bare string.

    ``isinstance("nope", Sequence)`` is True, so a naive check would let a stray
    string through and then iterate its characters.
    """
    return isinstance(value, Sequence) and not isinstance(value, str | bytes)


class HttpTvMazeGateway(TvMazeGateway):
    """Translates domain calls into TVMaze HTTP requests.

    Failures are normalised into application errors so the use cases never see
    an ``httpx`` exception.
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 5.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._max_retries = max(max_retries, 0)
        # The adapter owns the absolute URL. It cannot rely on the injected client
        # carrying a base_url, because that same client is shared with the AI
        # providers and must stay origin-agnostic.
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    async def search(self, term: SearchTerm) -> Sequence[Series]:
        payload = await self._get_json("/search/shows", params={"q": str(term)})
        if not _is_json_array(payload):
            raise ExternalServiceError("Unexpected TVMaze search payload")

        results: list[Series] = []
        for row in payload:
            show = row.get("show") if isinstance(row, Mapping) else None
            if not isinstance(show, Mapping):
                continue
            with mapped_payload_errors():
                results.append(to_series(show))
        return tuple(results)

    async def get_series(self, series_id: SeriesId) -> Series:
        payload = await self._get_json(f"/shows/{series_id}")
        if not isinstance(payload, Mapping):
            raise ExternalServiceError("Unexpected TVMaze show payload")
        with mapped_payload_errors():
            return to_series(payload)

    async def get_episodes(self, series_id: SeriesId) -> EpisodeGuide:
        payload = await self._get_json(f"/shows/{series_id}/episodes")
        if not _is_json_array(payload):
            raise ExternalServiceError("Unexpected TVMaze episodes payload")

        episodes = []
        for row in payload:
            if not isinstance(row, Mapping):
                continue
            with mapped_payload_errors():
                episodes.append(to_episode(row, series_id))
        return EpisodeGuide.from_episodes(series_id, episodes)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        logger.debug("catalogue request url=%s params=%s", url, params)

        async def attempt() -> httpx.Response:
            return await self._client.get(url, params=params)

        try:
            response = await retrying_call(
                attempt, attempts=self._max_retries + 1
            )
        except httpx.HTTPError as exc:
            logger.warning("catalogue transport failure path=%s error=%s", path, exc)
            raise ExternalServiceError(f"TVMaze is unreachable: {exc}") from exc

        if response.status_code == httpx.codes.NOT_FOUND:
            raise ResourceNotFound(f"TVMaze has no resource at {path}")
        if response.status_code >= httpx.codes.BAD_REQUEST:
            logger.warning(
                "catalogue error response path=%s status=%s", path, response.status_code
            )
            raise ExternalServiceError(
                f"TVMaze answered {response.status_code} for {path}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ExternalServiceError("TVMaze answered with invalid JSON") from exc


@contextmanager
def mapped_payload_errors() -> Iterator[None]:
    """Turn malformed upstream rows into ``ExternalServiceError``.

    A mapping failure is not a bug in our code: it means the catalogue changed
    shape. Reporting it as a dependency failure keeps the HTTP layer honest.
    """
    try:
        yield
    except InvalidValue as exc:
        logger.warning("catalogue payload rejected: %s", exc)
        raise ExternalServiceError(f"Malformed catalogue payload: {exc}") from exc
