"""Time port.

Timestamps must be injectable: tests assert on comment ordering and on the
``watched_at`` value without sleeping.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime


class Clock(ABC):
    """Source of the current time."""

    @abstractmethod
    def now(self) -> datetime:
        """Timezone aware ``datetime``."""


class SystemClock(Clock):
    """Production clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)
