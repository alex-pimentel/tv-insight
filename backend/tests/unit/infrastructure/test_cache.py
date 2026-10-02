"""Level 2/3: the TTL cache and its concurrency guard."""

from __future__ import annotations

import asyncio

import pytest

from tv_insight.infrastructure.cache import AsyncTtlCache


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


async def test_second_call_is_served_from_cache() -> None:
    time_source = FakeTime()
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(60, time_source=time_source)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        return 42

    first, hit_first = await cache.get_or_create("k", factory)
    second, hit_second = await cache.get_or_create("k", factory)

    assert (first, hit_first) == (42, False)
    assert (second, hit_second) == (42, True)
    assert calls == 1


async def test_entry_expires_after_ttl() -> None:
    time_source = FakeTime()
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(30, time_source=time_source)
    calls = 0

    async def factory() -> int:
        nonlocal calls
        calls += 1
        return calls

    await cache.get_or_create("k", factory)
    time_source.advance(31)
    value, hit = await cache.get_or_create("k", factory)

    assert hit is False
    assert value == 2


async def test_key_is_independent() -> None:
    cache: AsyncTtlCache[str, str] = AsyncTtlCache(60)
    assert (await cache.get_or_create("a", _const("A")))[0] == "A"
    assert (await cache.get_or_create("b", _const("B")))[0] == "B"


async def test_none_is_a_valid_cached_value() -> None:
    cache: AsyncTtlCache[str, str | None] = AsyncTtlCache(60)

    await cache.get_or_create("k", _const(None))
    value, hit = await cache.get_or_create("k", _const("other"))

    assert value is None
    assert hit is True


async def test_concurrent_misses_call_the_factory_once() -> None:
    cache: AsyncTtlCache[str, str] = AsyncTtlCache(60)
    calls = 0

    async def slow() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "value"

    results = await asyncio.gather(*(cache.get_or_create("k", slow) for _ in range(25)))

    assert calls == 1
    assert {value for value, _ in results} == {"value"}


async def test_invalidate_forces_a_refetch() -> None:
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(60)
    await cache.get_or_create("k", _const(1))
    cache.invalidate("k")

    value, hit = await cache.get_or_create("k", _const(2))

    assert (value, hit) == (2, False)


async def test_max_entries_evicts_the_least_recently_used() -> None:
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(60, max_entries=2)
    await cache.get_or_create("a", _const(1))
    await cache.get_or_create("b", _const(2))
    await cache.get_or_create("c", _const(3))

    value, hit = await cache.get_or_create("a", _const(99))

    assert (value, hit) == (99, False)


async def test_clear_empties_the_cache() -> None:
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(60)
    await cache.get_or_create("k", _const(1))
    cache.clear()

    value, hit = await cache.get_or_create("k", _const(2))

    assert (value, hit) == (2, False)


@pytest.mark.parametrize("ttl", [0.0, -1.0])
async def test_non_positive_ttl_never_hits(ttl: float) -> None:
    cache: AsyncTtlCache[str, int] = AsyncTtlCache(ttl)

    await cache.get_or_create("k", _const(1))
    _, hit = await cache.get_or_create("k", _const(1))

    assert hit is False


def _const(value: object):  # noqa: ANN202
    async def factory() -> object:
        return value

    return factory
