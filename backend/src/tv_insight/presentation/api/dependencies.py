"""FastAPI dependencies.

Two responsibilities only: hand the request a container, and make sure the
request carries a viewer identity. No business logic.
"""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request, Response

from tv_insight.infrastructure.composition import Container

VIEWER_COOKIE = "tv_insight_viewer"
VIEWER_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
VIEWER_ID_MAX_LENGTH = 64


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_viewer_id(request: Request, response: Response) -> str:
    """Read the viewer identity from a cookie, minting one when absent.

    The assignment has no login, but "watched" state and comments must survive a
    reload. A random, http-only cookie is the smallest thing that achieves that
    without inventing an account system.
    """
    existing = request.cookies.get(VIEWER_COOKIE, "")
    if 0 < len(existing) <= VIEWER_ID_MAX_LENGTH and existing.isascii():
        return existing

    fresh = uuid4().hex
    response.set_cookie(
        VIEWER_COOKIE,
        fresh,
        max_age=VIEWER_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return fresh


ViewerIdDep = Annotated[str, Depends(get_viewer_id)]
