"""A small TTL cache.

Used as a decorator around the catalogue gateway: TVMaze is rate limited and the
same series/show payload is fetched on nearly every interaction. The cache is
intentionally tiny, in-process and lock protected against the "thundering herd"
(a burst of identical requests triggers one upstream call, not N).
"""

from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

K = TypeVar("K")
V = TypeVar("V")


class _Missing:
    """Sentinel so ``None`` can be a legitimate cached value."""


_MISSING = _Missing()


@dataclass(slots=True)
class _Entry(Generic[V]):
    value: V
    expires_at: float


class AsyncTtlCache(Generic[K, V]):
    """In-memory, per-key-locked, LRU bounded TTL cache."""

    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int = 512,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._now = time_source
        self._entries: OrderedDict[K, _Entry[V]] = OrderedDict()
        self._locks: dict[K, asyncio.Lock] = {}
        self._guard = asyncio.Lock()

    async def get_or_create(
        self, key: K, factory: Callable[[], Awaitable[V]]
    ) -> tuple[V, bool]:
        """Return ``(value, from_cache)``, calling ``factory`` at most once per key."""
        hit = self._lookup(key)
        if hit is not _MISSING:
            return cast("V", hit), True

        lock = await self._lock_for(key)
        async with lock:
            hit = self._lookup(key)
            if hit is not _MISSING:
                return cast("V", hit), True
            value = await factory()
            self._store(key, value)
            await self._release(key)
            return value, False

    def invalidate(self, key: K) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def _lookup(self, key: K) -> V | _Missing:
        entry = self._entries.get(key)
        if entry is None:
            return _MISSING
        if entry.expires_at <= self._now():
            self._entries.pop(key, None)
            return _MISSING
        self._entries.move_to_end(key)
        return entry.value

    def _store(self, key: K, value: V) -> None:
        self._entries[key] = _Entry(value=value, expires_at=self._now() + self._ttl)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    async def _lock_for(self, key: K) -> asyncio.Lock:
        async with self._guard:
            return self._locks.setdefault(key, asyncio.Lock())

    async def _release(self, key: K) -> None:
        async with self._guard:
            self._locks.pop(key, None)
