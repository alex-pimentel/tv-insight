"""Errors raised by the domain model.

Infrastructure adapters translate their own failures into these types so the
application layer never has to know which database or HTTP client is in use.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every error raised by the domain."""


class InvalidValue(DomainError):
    """A value object or entity was built with data that violates its rules."""


class NotFound(DomainError):
    """A requested aggregate does not exist."""
