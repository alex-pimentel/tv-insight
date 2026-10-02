"""Health endpoint.

Reports the database connectivity and which AI providers are configured, so a
Jenkins smoke test (or a human) can tell a broken deployment from a missing
token at a glance.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from tv_insight.infrastructure.ai.factory import describe_providers
from tv_insight.presentation.api.dependencies import ContainerDep
from tv_insight.presentation.api.schemas import HealthModel, ProviderStatus

router = APIRouter(tags=["health"])

VERSION = "1.0.0"


@router.get("/health", response_model=HealthModel, summary="Liveness and readiness")
async def health(container: ContainerDep, response: Response) -> HealthModel:
    database_ok = await container.database_health()  # type: ignore[misc]
    if not database_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthModel(
        status="ok" if database_ok else "degraded",
        version=VERSION,
        database="up" if database_ok else "down",
        insights=[
            ProviderStatus(
                provider=info.name, available=info.available, model=info.model
            )
            for info in describe_providers(container.insight_provider)
        ],
    )
