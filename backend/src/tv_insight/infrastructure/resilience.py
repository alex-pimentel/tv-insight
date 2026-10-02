"""Resilience primitives.

Retry lives in the adapters, never in the use cases: "the catalogue timed out" is
an infrastructure concern that must not leak into business orchestration.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

RETRYABLE_HTTP = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
)


async def retrying_call(
    operation: Callable[[], Awaitable[httpx.Response]],
    *,
    attempts: int,
    backoff_seconds: float = 0.25,
    max_backoff_seconds: float = 4.0,
    retry_on: tuple[type[Exception], ...] = RETRYABLE_HTTP,
) -> httpx.Response:
    """Run ``operation`` with exponential backoff on transient failures.

    Only transport level errors are retried: a 500 from the catalogue is a
    business answer ("this thing is broken"), not something to hammer.
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max(attempts, 1)),
        wait=wait_exponential(multiplier=backoff_seconds, max=max_backoff_seconds),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    ):
        with attempt:
            return await operation()
    raise AssertionError("unreachable: AsyncRetrying always returns or raises")
