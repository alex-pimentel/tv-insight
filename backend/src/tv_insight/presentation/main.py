"""Process entry point.

``python -m tv_insight.presentation.main`` and the ``tv-insight`` console script
both land here.
"""

from __future__ import annotations

import uvicorn

from tv_insight.infrastructure.config import get_settings
from tv_insight.infrastructure.logging import configure_logging
from tv_insight.presentation.app import create_app


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",  # noqa: S104 - containerised service
        port=settings.app_port,
        log_config=None,
        access_log=not settings.is_production,
    )


if __name__ == "__main__":
    run()
