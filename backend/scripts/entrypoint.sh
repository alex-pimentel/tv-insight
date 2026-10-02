#!/usr/bin/env bash
#
# Container entrypoint: apply the schema, then hand over to the app.
#
# Migrations run here (and not in the application process) so the API never has
# to know about Alembic, and so the ordering is obvious to an operator reading
# `docker compose logs`.
set -euo pipefail

echo "[entrypoint] applying database migrations"
alembic -c /app/alembic.ini upgrade head

echo "[entrypoint] starting tv-insight on port ${APP_PORT:-7777}"
exec python -m tv_insight.presentation.main
