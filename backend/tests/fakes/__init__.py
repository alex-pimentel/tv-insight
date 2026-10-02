"""Test doubles.

Hand written fakes instead of a mocking library: they implement the real ports,
so if a port changes the fakes stop satisfying the interface and the tests keep
telling the truth. They are shared by the unit and the integration suites.
"""

from tests.fakes.clock import FixedClock
from tests.fakes.insight import (
    RecordingInsightProvider,
    ScriptedInsightProvider,
    UnavailableInsightProvider,
)
from tests.fakes.persistence import (
    InMemoryCommentRepository,
    InMemoryInsightRepository,
    InMemoryUnitOfWork,
    InMemoryWatchedEpisodeRepository,
)
from tests.fakes.tvmaze import InMemoryTvMazeGateway

__all__ = [
    "FixedClock",
    "InMemoryCommentRepository",
    "InMemoryInsightRepository",
    "InMemoryTvMazeGateway",
    "InMemoryUnitOfWork",
    "InMemoryWatchedEpisodeRepository",
    "RecordingInsightProvider",
    "ScriptedInsightProvider",
    "UnavailableInsightProvider",
]
