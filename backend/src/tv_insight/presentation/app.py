"""Application factory.

Everything the web process needs is built here, from a ``Settings`` object, so a
test can construct the same app with test doubles and no environment variables.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tv_insight.infrastructure.composition import Container
from tv_insight.infrastructure.config import Settings, get_settings
from tv_insight.infrastructure.logging import configure_logging, get_logger
from tv_insight.presentation.api.errors import register_error_handlers
from tv_insight.presentation.api.routers import (
    comments,
    episodes,
    health,
    insights,
    series,
    session,
)

logger = get_logger(__name__)

API_PREFIX = "/api"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(
    settings: Settings | None = None,
    container: Container | None = None,
) -> FastAPI:
    """Build the ASGI application.

    ``container`` is injectable so integration tests can supply in-memory fakes
    and skip the network, the database and the LLM entirely.
    """
    resolved = settings or get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owns_container = container is None
        app.state.container = container or Container.build(resolved)
        logger.info("tv-insight started env=%s", resolved.app_env)
        try:
            yield
        finally:
            if owns_container:
                await app.state.container.shutdown()
            logger.info("tv-insight stopped")

    app = FastAPI(
        title="tv-insight",
        description=(
            "Interactive TV series experience: search, episode tracking, "
            "comments and AI powered insights over the public TVMaze API."
        ),
        version="1.0.0",
        lifespan=lifespan,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)
    _register_routers(app)
    _mount_frontend(app, resolved)

    return app


def _register_routers(app: FastAPI) -> None:
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(session.router, prefix=API_PREFIX)
    app.include_router(series.router, prefix=API_PREFIX)
    app.include_router(episodes.router, prefix=API_PREFIX)
    app.include_router(comments.router, prefix=API_PREFIX)
    app.include_router(insights.router, prefix=API_PREFIX)


def resolve_static_dir(settings: Settings) -> Path:
    """Where the built single page application lives.

    ``STATIC_DIR`` lets the container point at a volume or a copied folder without
    rebuilding the package; the default keeps local development working with the
    files sitting next to this module.
    """
    if settings.static_dir:
        return Path(settings.static_dir).expanduser().resolve()
    return STATIC_DIR


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve the built single page application, when it exists.

    In development the Vite dev server hosts the UI and proxies ``/api`` here, so
    the absence of the static folder is expected and not an error.
    """
    static_dir = resolve_static_dir(settings)
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    index = static_dir / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def spa(full_path: str) -> FileResponse | JSONResponse:
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "NotFound"})
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            status_code=404,
            content={
                "error": "FrontendNotBuilt",
                "detail": "Run `npm run build` in frontend/, or use the Vite dev server.",
            },
        )
