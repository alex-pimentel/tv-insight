"""Deterministic time for assertions on ordering and timestamps."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tv_insight.application.ports.clock import Clock


class FixedClock(Clock):
    """Clock that advances by a fixed step every time it is read."""

    def __init__(
        self,
        start: datetime | None = None,
        step: timedelta = timedelta(minutes=1),
    ) -> None:
        self._current = start or datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        self._step = step

    def now(self) -> datetime:
        moment = self._current
        self._current = self._current + self._step
        return moment
