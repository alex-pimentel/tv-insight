"""Shared error responses.

Every router declares the same error vocabulary, so the OpenAPI document (and
therefore the generated TypeScript client and the Swagger UI) describes what a
failure actually looks like instead of only the happy path. The shape is
``{"error": ..., "detail": ...}`` for all of them.
"""

from __future__ import annotations

from typing import Any

from tv_insight.presentation.api.schemas import ErrorModel

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorModel, "description": "Invalid input"},
    404: {"model": ErrorModel, "description": "Unknown resource"},
    502: {"model": ErrorModel, "description": "Upstream catalogue failure"},
    503: {"model": ErrorModel, "description": "No insight provider available"},
}
