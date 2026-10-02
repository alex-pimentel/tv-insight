# tv-insight - developer entry points
#
# `make up` is the single command the assignment asks for: it builds the images
# and starts the application (7777) together with its database.

SHELL := /bin/bash
.DEFAULT_GOAL := help

BACKEND := backend
FRONTEND := frontend
VENV ?= $(BACKEND)/.venv
PY ?= $(VENV)/bin/python

.PHONY: help up down build logs ps restart migrate revision shell db-shell \
        install test test-backend test-frontend test-e2e lint typecheck fmt \
        run dev clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Docker (the single-command path)
# ---------------------------------------------------------------------------

up: ## Build and start the whole stack (app on :7777 + postgres)
	docker compose up --build -d
	@echo ""
	@echo "tv-insight is starting: http://localhost:$(or $(APP_PORT),7777)"
	@echo "Follow the logs with: make logs"

down: ## Stop the stack and keep the database volume
	docker compose down

clean: ## Stop the stack and delete the database volume
	docker compose down -v

build: ## Build the images without starting anything
	docker compose build

logs: ## Tail the application logs
	docker compose logs -f app

ps: ## Show container status
	docker compose ps

restart: ## Recreate the application container
	docker compose up -d --force-recreate app

migrate: ## Apply database migrations inside the running container
	docker compose exec app alembic -c /app/alembic.ini upgrade head

revision: ## Create a migration from the current models (m="message")
	docker compose exec app alembic -c /app/alembic.ini revision --autogenerate -m "$(m)"

db-shell: ## Open a psql session on the database container
	docker compose exec db psql -U $${POSTGRES_USER:-tvinsight} -d $${POSTGRES_DB:-tvinsight}

shell: ## Open a shell inside the application container
	docker compose exec app bash

# ---------------------------------------------------------------------------
# Local development (no docker)
# ---------------------------------------------------------------------------

install: ## Create the backend venv and install everything
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e "$(BACKEND)[dev]"
	cd $(FRONTEND) && npm install

run: ## Run the API locally (expects a reachable database)
	cd $(BACKEND) && $(abspath $(PY)) -m tv_insight.presentation.main

dev: ## Run the Vite dev server (proxies /api to :7777)
	cd $(FRONTEND) && npm run dev

# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

test: test-backend test-frontend ## Run every backend and frontend test

test-backend: ## Unit + integration backend tests with coverage (fails under 90%)
	cd $(BACKEND) && $(abspath $(PY)) -m pytest \
		--cov=tv_insight --cov-report=term-missing --cov-fail-under=90

test-frontend: ## Component tests (Vitest) with coverage thresholds
	cd $(FRONTEND) && npm run test:coverage

test-e2e: ## End to end tests (Playwright) in a container against the running stack
	docker compose --profile test run --rm e2e

lint: ## Ruff + ESLint
	cd $(BACKEND) && $(abspath $(PY)) -m ruff check .
	cd $(FRONTEND) && npm run lint --if-present

typecheck: ## mypy (strict) + tsc
	cd $(BACKEND) && $(abspath $(PY)) -m mypy
	cd $(FRONTEND) && npm run typecheck

fmt: ## Auto-fix formatting and imports (backend)
	cd $(BACKEND) && $(abspath $(PY)) -m ruff check --fix .
