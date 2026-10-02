"""Maps application and domain errors onto HTTP responses.

This is the only module that knows about status codes, which is why the use cases
can stay framework free.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tv_insight.application.errors import (
    ExternalServiceError,
    InvalidInput,
    ProviderUnavailable,
    ResourceNotFound,
)
from tv_insight.infrastructure.logging import get_logger

logger = get_logger(__name__)

_STATUS_BY_ERROR: dict[type[Exception], int] = {
    InvalidInput: 400,
    ResourceNotFound: 404,
    ExternalServiceError: 502,
    ProviderUnavailable: 503,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidInput)
    @app.exception_handler(ResourceNotFound)
    @app.exception_handler(ExternalServiceError)
    @app.exception_handler(ProviderUnavailable)
    async def handle_application_error(  # noqa: ANN202
        request: Request, exc: Exception
    ) -> JSONResponse:
        status = _STATUS_BY_ERROR.get(type(exc), 500)
        if status >= 500:
            logger.warning("%s on %s: %s", type(exc).__name__, request.url.path, exc)
        return JSONResponse(
            status_code=status,
            content={"error": type(exc).__name__, "detail": str(exc)},
        )
