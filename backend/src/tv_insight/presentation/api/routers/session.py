"""Guest session endpoints.

The assignment has no authentication, and the client's answer for the "do we need
registration?" question was *"some use as guest, use the session"*
(``docs/CLIENT-FEEDBACK.md``). So: a guest session carried by an httpOnly cookie,
plus a way to start a fresh one - useful in a demo to show that watched state and
comments are genuinely scoped to the session.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from tv_insight.presentation.api.dependencies import VIEWER_COOKIE

router = APIRouter(prefix="/session", tags=["session"])


class SessionModel(BaseModel):
    kind: str = "guest"


@router.get("", response_model=SessionModel, summary="Describe the current session")
async def read_session() -> SessionModel:
    """Confirms the session model without exposing the identifier.

    The cookie is httpOnly on purpose; the client only needs to know that it is
    browsing as a guest.
    """

    return SessionModel()


@router.post(
    "/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Start a new guest session",
)
async def reset_session(response: Response) -> None:
    """Discard the current guest identity.

    Deliberately does not mint the replacement here: the next request that needs a
    viewer will create one, which keeps the identity logic in a single place
    (``dependencies.get_viewer_id``).
    """

    response.delete_cookie(VIEWER_COOKIE, httponly=True, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
