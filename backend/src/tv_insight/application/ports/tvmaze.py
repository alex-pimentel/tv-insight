"""Port for the external TV catalogue.

The application only knows *what* it can ask for, never that the answer comes
from TVMaze over HTTP.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from tv_insight.domain.entities.guide import EpisodeGuide
from tv_insight.domain.entities.series import Series
from tv_insight.domain.value_objects import SearchTerm, SeriesId


class TvMazeGateway(ABC):
    """Read only access to a TV catalogue."""

    @abstractmethod
    async def search(self, term: SearchTerm) -> Sequence[Series]:
        """Return the series matching ``term``, catalogue order preserved."""

    @abstractmethod
    async def get_series(self, series_id: SeriesId) -> Series:
        """Return one series. Raises ``ResourceNotFound`` when unknown."""

    @abstractmethod
    async def get_episodes(self, series_id: SeriesId) -> EpisodeGuide:
        """Return the full episode guide of a series."""

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        """Release transport resources. Best effort, never raises."""
        return
