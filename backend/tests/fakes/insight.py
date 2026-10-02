"""Fake AI providers for deterministic tests."""

from __future__ import annotations

from collections.abc import Sequence

from tv_insight.application.errors import ProviderUnavailable
from tv_insight.application.ports.insight import (
    InsightProvider,
    InsightRequest,
    InsightResult,
)


class ScriptedInsightProvider(InsightProvider):
    """Returns queued answers and records what it was asked."""

    def __init__(self, name: str = "scripted", answers: Sequence[str] = ("Insight.",)) -> None:
        self._name = name
        self._answers = list(answers)
        self.requests: list[InsightRequest] = []
        self.refresh_calls: list[bool] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        self.requests.append(request)
        self.refresh_calls.append(refresh)
        text = self._answers.pop(0) if self._answers else "Insight."
        return InsightResult(text=text, provider=self._name)


class UnavailableInsightProvider(InsightProvider):
    """Always fails, to exercise the fallback chain."""

    def __init__(self, name: str = "unavailable", available: bool = True) -> None:
        self._name = name
        self._available = available
        self.attempts = 0

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return self._available

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        self.attempts += 1
        raise ProviderUnavailable(f"{self._name}: boom")


class RecordingInsightProvider(InsightProvider):
    """Minimal provider that echoes a marker, used to assert wiring."""

    def __init__(self, name: str = "recording", text: str = "A curated insight.") -> None:
        self._name = name
        self._text = text

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        return InsightResult(text=self._text, provider=self._name)
