# tv-insight

An interactive TV series experience built for the **Software Architect** technical
assignment: search series on the public [TVMaze](https://www.tvmaze.com/api) API,
browse episodes grouped by season, track what you watched, comment on series and
episodes, and get an **AI generated insight** about either.

The module is written to be a technical reference: the architecture, the trade-offs
and the tests matter as much as the features.

```
┌──────────────────────────────────────────────────────────────────────┐
│  React SPA  ──►  FastAPI  ──►  domain / application  ──►  PostgreSQL │
│                    │                                                  │
│                    └──►  TVMaze (HTTP)      └──►  LLM chain (HF →    │
│                                                   OpenRouter → rule) │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick start

Everything runs with a single command:

```bash
make up
```

Then open **http://localhost:7777**.

That is `docker compose up --build -d`: it builds the multi-stage image (Node
compiles the React app, Python runs the API), starts PostgreSQL 16, waits for it to
be healthy, applies the database migrations and serves the application on port
**7777**.

```bash
make logs     # follow the application logs
make ps       # container status
make down     # stop, keeping the database volume
make clean    # stop and drop the database volume
```

> The AI insight provider order defaults to `huggingface,openrouter,heuristic`.
> Without credentials the first two are skipped and the **offline rule based
> provider** answers, clearly flagged as `degraded`. To use a real model, copy
> `.env.example` to `.env` and fill in `HUGGINGFACE_API_TOKEN` and/or
> `OPENROUTER_API_KEY`.

## Features

| Requirement | Where it lives |
| --- | --- |
| Search series asynchronously (title, year, poster) | `GET /api/series/search?q=` · `SearchPage` |
| Series details: poster, summary, genres, episodes by season | `GET /api/series/{id}` · `SeriesPage` |
| Mark episodes as watched, persisted across navigation and reloads | `PUT /api/series/{id}/episodes/{eid}/watched` · `SeasonAccordion` |
| Comments on a series or on a specific episode | `GET/POST /api/series/{id}/comments` |
| AI insight for a series or an episode, generated **on demand** | `GET /api/series/{id}/insight` · `InsightPanel` |

There is no login. A guest session carried by an `httpOnly` cookie identifies the
visitor, so watched state and comments survive reloads without inventing an account
system — and `POST /api/session/reset` starts a fresh one.

### How the AI feature behaves

It follows a small, explicit decision matrix:

1. **Every explicit request tries the model providers first.** Pressing *View
   insights* (or *Regenerate*) always attempts a fresh generation, so the answer is
   current. Nothing is requested just because a details page was opened.
2. **If the providers fail and a stored insight exists, the stored one is served.**
   The `insights` table only ever holds answers a real model produced, so it is the
   "last known good" answer — flagged `cached` and explained in `notes`.
3. **If the providers fail and the store is empty, the local heuristic tier
   answers**, flagged `degraded`, so the feature never disappears.

The chain is `huggingface → heuristic` by default; a second model vendor is opt-in
through `AI_PROVIDER_ORDER`. `AI_INSIGHT_COMMENT_THRESHOLD` (default **0**) controls
cost: a positive value restores the "reuse until N new comments exist" window, and
`AI_INSIGHT_CACHE_TTL_SECONDS` (default **0**) enables an in-process burst cache.

The UI is honest about provenance: it shows which provider answered, whether the
answer was reused, whether it was degraded, and how many comments it is based on.

## Architecture in one screen

Clean Architecture, with the dependency rule enforced by the import direction:

| Layer | Package | May import |
| --- | --- | --- |
| Domain | `tv_insight/domain` | standard library only |
| Application | `tv_insight/application` | domain |
| Infrastructure | `tv_insight/infrastructure` | domain, application, third party |
| Presentation | `tv_insight/presentation` | application, infrastructure |

```
src/tv_insight/
├── domain/           entities · value objects · repository ports · domain services
├── application/      ports · DTOs · one class per use case
├── infrastructure/   TVMaze client · AI providers · SQLAlchemy · composition root
└── presentation/     FastAPI routers · static SPA
```

All wiring happens in `infrastructure/composition.py`; nothing else in the codebase
imports two layers at once. Full detail, diagrams and the reasoning behind each
pattern: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). The decisions and the
alternatives that were rejected: [`docs/TRADEOFFS.md`](docs/TRADEOFFS.md).

### Design patterns used, and why

Repository · Unit of Work · Dependency Injection (composition root) · Strategy +
Composite (AI provider chain) · Decorator (caching of catalogue and insights) ·
Adapter (TVMaze, LLM vendors) · Value Object · DTO/Mapper · Null-ish safe terminal
fallback.

## Testing

Four levels, matching the "component / configuration item / subsystem / system"
ladder:

| Level | Scope | Count | Notes |
| --- | --- | --- | --- |
| 1. Domain unit | value objects, entities, season grouping, progress, prompt rules, insight freshness | 96 | no I/O at all, milliseconds |
| 2. Use case unit | every use case against in-memory fakes, including the insight store | 51 | no framework, no database |
| 3. Infrastructure unit | mappers, HTTP adapter, cache, provider chain, heuristic, config, composition | 166 | `respx` for HTTP, injected clocks |
| 4. Presentation + integration | app factory/lifespan, session, the real ASGI contract and real PostgreSQL repositories | 55 | DB tests skip automatically without a database |
| 5. System / E2E | built bundle in Chromium against the real API and database | 11 | official Playwright image |

```bash
make test          # backend + frontend
make test-e2e      # browser suite against the running stack (docker compose up first)
```

Backend: **380 tests**, **98 % coverage without a database and 99.8 % with
PostgreSQL**, `ruff` clean, `mypy --strict` clean.
Frontend: `tsc` strict clean, **ESLint clean (type-aware)**, **93 Vitest component
tests**, 99 % statement coverage.

Coverage is a build gate, not a report: `pytest --cov-fail-under=90` in the
Makefile, CI and Jenkinsfile, and thresholds in `vite.config.ts`. There is a
detailed, line-by-line justification of the remaining uncovered lines in
[`docs/study/06-testes-cobertura.md`](docs/study/06-testes-cobertura.md).

Frontend linting is type-aware and includes `@typescript-eslint/no-deprecated`, so a
deprecated API (such as the `FormEvent` type that React 19 retired) fails the build
instead of showing up as an editor squiggle.

The browser suite runs inside the official Playwright image via
`docker compose --profile test run --rm e2e`, so it does not depend on the host
having browsers or their system libraries.

Looking for the deep dive? [`docs/study/`](docs/study/) is a full study guide
(folder-by-folder anatomy, why each design pattern was chosen, technology
trade-offs, coverage breakdown and a Q&A rehearsal for the presentation).

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | liveness, database status, which AI providers are configured |
| `GET` | `/api/session` | confirms the guest session model |
| `POST` | `/api/session/reset` | starts a new guest session |
| `GET` | `/api/series/search?q=` | search the catalogue |
| `GET` | `/api/series/{id}` | series, seasons, watched progress and comments |
| `GET` | `/api/series/{id}/episodes/{episode_id}` | one episode plus the next one |
| `PUT` | `/api/series/{id}/episodes/{episode_id}/watched` | `{"watched": true\|false}` |
| `GET` | `/api/series/{id}/comments[?episode_id=]` | list comments |
| `POST` | `/api/series/{id}/comments` | `{"text": "...", "episode_id": null}` |
| `GET` | `/api/series/{id}/insight[?refresh=true]` | insight for a series (stored or generated) |
| `GET` | `/api/series/{id}/episodes/{episode_id}/insight` | insight for an episode |

An insight response reports its own provenance, including how many comments it was
built from and whether it was reused:

```json
{
  "text": "…",
  "provider": "heuristic",
  "degraded": true,
  "cached": true,
  "based_on_comment_count": 1,
  "notes": ["Served from the stored insight; no provider was called."]
}
```

Interactive docs: <http://localhost:7777/api/docs>.

Errors always answer with the same shape, mapped from the application's error
taxonomy (`InvalidInput` → 400, `ResourceNotFound` → 404, `ExternalServiceError` →
502, `ProviderUnavailable` → 503):

```json
{ "error": "ResourceNotFound", "detail": "Unknown series 424242" }
```

## Configuration

Everything is environment driven, validated once at start up by
`infrastructure/config.py`, and documented in [`.env.example`](.env.example).
`DATABASE_URL` overrides the assembled connection string. `AI_PROVIDER_ORDER`
controls the fallback chain; `heuristic` is always forced to the end so an insight
is always produced.

## Project layout

```
.
├── backend/            FastAPI service (Clean Architecture)
│   ├── src/tv_insight/ domain · application · infrastructure · presentation
│   ├── migrations/     Alembic
│   └── tests/          unit (domain, application, infrastructure) + integration
├── frontend/           React 19 + Vite + TypeScript + Tailwind 4
│   ├── src/            api client · components · pages · hooks
│   └── e2e/            Playwright specs
├── docs/               architecture, trade-offs, presentation script
├── Dockerfile          multi-stage: Node build → slim Python runtime
├── Dockerfile.e2e      Playwright image for the browser suite
├── docker-compose.yml  file format 3.3 · app (7777) + postgres 16
├── Jenkinsfile         the pipeline this project is meant to run in
└── Makefile            every entry point, including the single-command start
```

## Local development without Docker

```bash
make install                 # backend venv + frontend dependencies
docker compose up -d db      # just the database
cd backend && DATABASE_URL=postgresql+asyncpg://tvinsight:tvinsight@localhost:5432/tvinsight \
  alembic upgrade head
make run                     # uvicorn on :7777
make dev                     # Vite dev server on :5173, proxies /api to :7777
```

The Vite dev server proxies `/api` to the backend, so the browser stays
same-origin and the viewer cookie behaves exactly as in production.

## License

MIT — see `LICENSE`.
