"""Port for the AI insight provider (Strategy pattern).

Every provider implements the same three members. Swapping HuggingFace for
OpenRouter, or for the deterministic rule based provider, is a wiring change in
the composition root - no use case is touched.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from tv_insight.domain.services.insight_prompt import InsightPrompt, InsightSubject


@dataclass(frozen=True, slots=True)
class InsightRequest:
    """Everything a provider may use.

    ``prompt`` is what a language model needs; ``subject`` is the structured
    original. Passing both means a provider can be an LLM *or* a deterministic
    generator without the port favouring either.
    """

    prompt: InsightPrompt
    subject: InsightSubject


@dataclass(frozen=True, slots=True)
class InsightResult:
    """What a provider hands back.

    ``provider`` records who actually answered, ``notes`` explains any degradation
    (which tier was skipped and why) so the caller can be transparent about it.
    Caching is deliberately *not* reported here: whether the answer was reused is
    a decision of the application (the stored insight), not of the provider.
    """

    text: str
    provider: str
    degraded: bool = False
    notes: tuple[str, ...] = field(default_factory=tuple)


class InsightProvider(ABC):
    """Generates a short insight from a request."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable identifier reported back to the caller (e.g. ``huggingface``)."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider has the credentials it needs to be tried."""

    @abstractmethod
    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        """Return the insight.

        ``refresh`` asks the implementation to bypass any cache it may hold.
        Implementations raise ``ProviderUnavailable`` (or
        ``ExternalServiceError``) on failure so the fallback chain can react.
        """
