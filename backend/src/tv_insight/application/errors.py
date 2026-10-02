"""Errors signalled by the application layer.

The presentation layer maps these to HTTP status codes, which keeps FastAPI out
of the use cases and the domain.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from tv_insight.domain.exceptions import InvalidValue, NotFound


class ApplicationError(Exception):
    """Base class for every application level failure."""


class ResourceNotFound(ApplicationError):
    """The requested resource does not exist (HTTP 404)."""


class InvalidInput(ApplicationError):
    """The caller sent something the use case refuses (HTTP 400)."""


class ExternalServiceError(ApplicationError):
    """An upstream dependency (TVMaze) failed (HTTP 502)."""


class ProviderUnavailable(ApplicationError):
    """An AI provider could not produce an answer (drives the fallback chain)."""


@contextmanager
def translated_domain_errors() -> Iterator[None]:
    """Re-raise domain failures as application errors.

    Keeps the vocabulary of the outer edge limited to ``ApplicationError`` while
    still letting value objects guard their own invariants.
    """
    try:
        yield
    except InvalidValue as exc:
        raise InvalidInput(str(exc)) from exc
    except NotFound as exc:
        raise ResourceNotFound(str(exc)) from exc
