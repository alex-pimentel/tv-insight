"""Decorator that memoises the provider chain.

This is a *transparent* performance layer, not the insight cache: it absorbs a
burst of identical concurrent requests (and a repeated "Regenerate" within the
TTL) so the vendor is not billed twice for the same prompt. Whether an insight is
*allowed* to be reused is a business rule owned by ``GenerateInsight`` and backed
by the durable ``insights`` table - see ``docs/CLIENT-FEEDBACK.md``.
"""

from __future__ import annotations

import hashlib

from tv_insight.application.ports.insight import (
    InsightProvider,
    InsightRequest,
    InsightResult,
)
from tv_insight.infrastructure.cache import AsyncTtlCache


class CachingInsightProvider(InsightProvider):
    def __init__(
        self,
        inner: InsightProvider,
        cache: AsyncTtlCache[str, InsightResult],
    ) -> None:
        self._inner = inner
        self._cache = cache

    @property
    def name(self) -> str:
        return self._inner.name

    @property
    def inner(self) -> InsightProvider:
        """The wrapped provider, so diagnostics can inspect the real chain."""
        return self._inner

    def is_available(self) -> bool:
        return self._inner.is_available()

    async def generate(
        self, request: InsightRequest, *, refresh: bool = False
    ) -> InsightResult:
        key = self._key(request)
        if refresh:
            self._cache.invalidate(key)

        result, _ = await self._cache.get_or_create(
            key, lambda: self._inner.generate(request, refresh=refresh)
        )
        return result

    @staticmethod
    def _key(request: InsightRequest) -> str:
        fingerprint = f"{request.prompt.system}\x00{request.prompt.user}".encode()
        return hashlib.sha256(fingerprint).hexdigest()
