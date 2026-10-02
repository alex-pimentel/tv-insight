"""Engine and session factory construction."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tv_insight.infrastructure.config import Settings

SessionFactory = async_sessionmaker[AsyncSession]


def create_engine(settings: Settings) -> AsyncEngine:
    """Build the async engine.

    ``pool_pre_ping`` protects against connections killed by the database
    container restarting, which is the common failure mode in a compose setup.
    """
    return create_async_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        future=True,
    )


def create_session_factory(engine: AsyncEngine) -> SessionFactory:
    # expire_on_commit=False keeps loaded attributes usable after commit, so the
    # repositories can return domain objects without a second query.
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def ping(engine: AsyncEngine) -> bool:
    """Cheap liveness probe used by ``GET /api/health``."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - a health check must never raise
        return False
    return True
