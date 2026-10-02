"""Declarative base for the persistence models.

The models here are *persistence* models, not domain entities: the repositories
translate between the two. That separation is what lets the domain change shape
without a database migration, and vice versa.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for every ORM model."""
