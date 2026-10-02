# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 - build the React single page application.
# Node exists only here: nothing about it survives into the runtime image.
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend

WORKDIR /build

# Dependency manifests first, so a source-only change does not reinstall them.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 - Python runtime with the API and the compiled UI.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    APP_PORT=7777 \
    STATIC_DIR=/app/static

WORKDIR /app

# curl is used by the compose healthcheck; keep the layer minimal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install the package (and therefore all dependencies) before copying the rest,
# so editing documents or migrations does not invalidate the dependency layer.
COPY backend/pyproject.toml backend/README.md ./
COPY backend/src/ ./src/
RUN pip install .

COPY backend/alembic.ini ./
COPY backend/migrations/ ./migrations/
COPY backend/scripts/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# The compiled UI produced by stage 1.
COPY --from=frontend /build/dist /app/static

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 7777

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS "http://localhost:${APP_PORT}/api/health" || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
