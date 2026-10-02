# Trade-offs and decisions

An architecture is a set of decisions with reasons. This file records the ones that
matter, what was rejected, and what would change the answer. It is the document to
read before the peer review.

The assignment weights *"separation of concerns, extensibility, trade-offs"* at
30 %, so the rejected options are as important as the chosen ones.

---

## Decision log

### D1 - Clean Architecture with four layers, for a small scope

**Chosen.** `domain → application → infrastructure → presentation`, dependency rule
enforced by import direction.

**Rejected:** a single `app/` package with routers, services and models side by
side. It would have been ~40 % fewer files.

**Why.** The scope is small, which is exactly why the architecture has to be
justified by testability rather than by size. The layering pays off in three
concrete places today:

1. `tests/unit/domain` needs no fixtures, no database and no HTTP, because the
   domain imports nothing.
2. The AI feature is testable with zero network because `InsightProvider` is a
   port: `FallbackInsightProvider` and the whole chain are covered by fast tests.
3. Swapping Postgres for another store is one class in `infrastructure/db`.

**Cost.** More files, and mapping between domain entities, application DTOs and API
schemas looks like ceremony in a project this size. Accepted, because the assignment
explicitly asks for a reference implementation.

---

### D2 - The prompt is built in the domain, not in the adapter

**Chosen.** `InsightPromptComposer` is a **domain service**. Providers receive an
`InsightRequest` that carries both the composed prompt *and* the structured
subject.

**Rejected:** building messages inside each vendor adapter.

**Why.** *"The insight is based on the summary, genres and comments, and stays
under N words"* is a product rule, not an HTTP detail. Keeping it in the domain
means it is unit tested in isolation, and every vendor produces equivalent input.
Passing the structured subject as well lets the rule based provider be a
deterministic generator instead of a parser of its own prompt.

**Cost.** The port carries a slightly richer object. Worth it.

---

### D3 - Provider chain: primary model → local heuristic, with honest provenance

**Chosen.** A `FallbackInsightProvider` composite in front of every vendor, wrapped
in a caching decorator. The default chain is `huggingface → heuristic`; the second
model vendor (`openrouter`) is available but opt-in through `AI_PROVIDER_ORDER`.
`heuristic` is always forced last and never fails.

**Why.** The assignment weights *"isolation, provider independence, fallback
strategy"* at 10 %, and "handle failures gracefully" explicitly. A chain that ends
in a deterministic provider means the feature is demonstrable on a laptop with no
network, in a Jenkins VM with no secrets, and in a live demo where the free tier is
rate limited. A second *model* tier was deliberately left out of the default after
the client's answer to the fallback question ("the idea is to create a heuristic
process") — see D15 and [`CLIENT-FEEDBACK.md`](CLIENT-FEEDBACK.md).

**Honesty over illusion.** The response reports `provider`, `degraded`, `cached`,
`based_on_comment_count` and `notes`, and the UI shows *"via heuristic - offline
fallback"* plus *"reused"* when the stored insight answered. A degraded answer that
pretends to be a model is worse than an honest one, especially under review.

**Cost.** Two caching layers now exist; they are documented as having different
purposes (D14). A stale insight can hide a newly configured provider until the
threshold is crossed; *Regenerate* bypasses both layers deliberately.

---

### D4 - Provider exceptions are caught broadly, at one boundary

`FallbackInsightProvider.generate` catches `Exception` (with `noqa: BLE001`) around
each vendor call, logs it, and records it as a note.

**Why.** A provider is a plugin boundary. If one vendor raises something unexpected,
the healthy tier behind it must still be allowed to answer - that is the entire
point of having a chain. Every swallowed exception is logged and surfaced, so
nothing is hidden.

**Rejected:** letting unexpected exceptions propagate so bugs are loud. That
presents a broken feature to a user when a working fallback exists.

---

### D5 - Aggregate the detail screen on the server

**Chosen.** `GET /api/series/{id}` returns series + seasons + watched progress +
comments.

**Rejected:** separate endpoints for the guide, the progress and the comments, with
the SPA orchestrating them.

**Why.** One round trip, one loading state, one error state. Against a rate limited
public API and a demo over a flaky connection, that is a measurable UX win.

**Cost.** `GetSeriesDetails` knows about four things. If the detail page grows
further (cast, similar series, ratings history), the right move is to split it into
a BFF-style composed endpoint or to add a dedicated `GET /summary`.

---

### D6 - PostgreSQL in a second container, with Alembic

**Chosen.** `postgres:16-alpine` + `alembic upgrade head` in the entrypoint.

**Rejected:** SQLite in a volume (simpler, no second container) and
`Base.metadata.create_all()` (simpler, no migration files).

**Why.** The assignment requires *"one container for the database"*, and the role
is about production systems: Alembic is what a real team uses, and `alembic check`
running clean is a cheap, strong guarantee that the schema and the models agree.
The first migration is hand written so cloning the repository does not require a
live database.

**Cost.** An extra moving part in start-up. Mitigated by `depends_on:
condition: service_healthy` plus the container healthcheck.

---

### D7 - No authentication; a cookie identifies the viewer

**Chosen.** `httpOnly`, `SameSite=Lax` cookie with a random id, minted on first
use.

**Rejected:** real auth (out of scope, and would dominate the assignment) and
`localStorage` (cannot be read server-side, so comments could not be attributed
without a second identity channel).

**Why.** *"Watched state must persist across navigation and reloads"* is the
requirement; a cookie is the smallest thing that satisfies it server-side and lets
comments be marked `mine`.

**Cost.** Anyone clearing cookies loses state; there is no cross-device identity.
This is a documented stand-in, not a security boundary.

---

### D8 - React + Vite + TypeScript, built in a multi-stage image

**Chosen.** Node stage compiles, slim Python stage runs. Node never exists at
runtime.

**Rejected:** server-rendered Jinja2 (fewer moving parts, but the role lists React
among the frameworks and rates UI/UX as preferred), and a no-build vanilla SPA
(smaller, but no component tests and no type safety).

**Why.** The job description asks for *"expertise in web technologies and
frameworks (React…)"*, *"experience with UI/UX"* and *"automate software testing at
multiple levels (component … system)"*. React + Vitest gives the component level;
Playwright in the official image gives the system level.

**Cost.** A larger image and a slower first build. The multi-stage split keeps the
runtime layer free of Node, and the dependency layers are cached.

---

### D9 - The browser suite shares the application's network namespace

**Chosen.** `docker compose --profile test run --rm e2e` with
`network_mode: service:app`, targeting `http://localhost:7777`.

**Why.** Recent Chromium builds upgrade plain HTTP navigations on non-loopback
hosts ("HTTPS-First Mode"), which against a container hostname surfaces as
`ERR_SSL_PROTOCOL_ERROR`. Loopback is exempt. Sharing the namespace lets the suite
hit the same process and port without disabling browser security features, and it
removes the need for the host to have browsers and their system libraries
installed - which matters for a Jenkins VM.

**Cost.** The e2e container cannot resolve other services (it does not need to).

---

### D10 - Hand written test doubles instead of a mocking framework

**Chosen.** `tests/fakes/` implements the real ports.

**Why.** Fakes implement the same abstract classes as production. If a port
changes, the fakes stop satisfying it and the suite tells the truth. Mocks assert
on call shapes and rot silently. The fakes are also reused by the integration suite
to build a fully wired `Container` (`tests/fakes/container.py`), which is how the
API is tested without network, database or LLM.

---

### D11 - The frontend API types are generated from the OpenAPI document

**Chosen.** `frontend/src/api/schema.d.ts` is generated (`make client`) from
`frontend/openapi.json`, which the backend dumps from its own app with
`make openapi` (`python -m tv_insight.presentation.openapi`). `types.ts` only
renames the generated schemas for the rest of the app.

**Rejected:** hand-writing the types next to `presentation/api/schemas.py`. It is
readable, but the two files drift and the drift is silent.

**Why.** The contract now has a single machine-readable source of truth, and CI
fails when it drifts: `npm run client:check` regenerates and compares, and the
backend job diffs a fresh dump against the committed `openapi.json`.

**Cost.** One build step (`openapi-typescript`, a dev dependency) and one rule the
generator applies: response properties are all required, because FastAPI always
emits the full object (`null` for absent values). Request bodies keep the schema's
own optionality, so `episode_id` stays optional where it truly is.

---

### D12 - Checks belong to the domain, but the action is idempotent in the database

`set_episode_watched` validates the episode against the cached guide (so a watched
row can never reference another series), and the composite primary key
`(viewer_id, episode_id)` makes the write idempotent.

**Cost.** The first toggle for a series costs a guide lookup; the TTL cache makes
every subsequent one free. Documented because it looks redundant until you know
about the cache.

---

### D13 - The insight is generated on an explicit user action

**Chosen.** Nothing is fetched until the user presses *View insights*.

**Rejected:** generating as part of the details page load.

**Why.** This came straight from the client ([`CLIENT-FEEDBACK.md`](CLIENT-FEEDBACK.md),
answer 1). It also bounds cost by intent rather than by page views, and it makes the
feature demonstrable: you can show the panel in its idle state and then show the
generation happening.

**Cost.** One extra click before the value appears. Mitigated by the idle state
explaining what will be generated from what.

---

### D14 - The insight is persisted as the "last known good" answer

**Chosen.** A new `insights` table keyed by `(target, target_id)` storing the text,
the provider, the `based_on_comment_count` and a `degraded` flag. On every explicit
request the model providers are tried first; the stored row is the fallback when
they fail. **Only answers produced by a real model are persisted**, so the stored
row can never be overwritten by the heuristic.

**Rejected:** keeping only the in-process TTL cache keyed by a hash of the prompt
(what existed before), and always serving the store while it is "fresh".

**Why.** The team's requirement is *current answers*: a click must attempt a fresh
generation, and the stored insight is the safety net, not the primary source. Making
the store model-only is what allows the failure path to prefer it over the heuristic
- a previously generated answer from a real model is worth more than a freshly
composed template.

**What happened to the client's cost rule.** It stays, as configuration:
`AI_INSIGHT_COMMENT_THRESHOLD` (default `0` = always regenerate) restores
"reuse until N new comments exist" with a positive value, and the rule is still a
domain method with its own tests (`StoredInsight.is_fresh_for`). Likewise
`AI_INSIGHT_CACHE_TTL_SECONDS` (default `0`) re-enables the in-process burst cache.
Both defaults are off because they would contradict "generate on every click".

**Cost.** The DB can be hit for a read that is usually followed by a write, and a
model call happens on every click - which is the point (freshness) and the trade-off
(spend). `Force regenerate` is gone: with the default it would be a no-op.

**Consequence.** The comment count is still recorded and displayed ("based on N
comments"), because it is useful provenance even when it does not gate anything.

---

### D15 - The fallback is a local heuristic, not a second model

**Chosen.** `heuristic` closes the chain and is the default second tier:
`AI_PROVIDER_ORDER=huggingface,heuristic`. Second model vendor (OpenRouter) is opt-in.

**Rejected:** `huggingface → openrouter → heuristic` as the default (the chain that
existed before), and answering "service unavailable" when the model fails.

**Why.** The client's answer to the fallback question was *"the idea is to create a
heuristic process"* (answer 3), which reads as a deliberate preference for a local,
free, always-available rule over paying for another model tier. The heuristic also
guarantees the feature never disappears.

**Cost.** A heuristic cannot understand meaning. It is therefore explicit about what
it does: it derives genres, a summary excerpt and recurring words from the comments,
and the result is flagged `provider: "heuristic"` + `degraded: true` so nobody
mistakes it for a model's answer.

**Kept from the same answer:** the *"show the saved insight"* option is implemented
as the last resort — if generation fails or returns nothing and a stored insight
exists, it is served, marked degraded, with a note.

---

### D16 - Guest session instead of registration

**Chosen.** A guest identity in an `httpOnly` cookie, plus `POST /api/session/reset`
to start a fresh one.

**Rejected:** a registration flow, and seeding three accounts with a switcher (the
two options in the question).

**Why.** The client said *"some use as guest, ou use the session"* (answer 4). A
guest session satisfies the actual requirement — watched state persists across
navigation and reloads — without inventing authentication, and the reset endpoint
makes the scoping demonstrable.

**Cost.** Clearing cookies loses the state, and there is no cross-device identity.
Documented as a stand-in rather than a security boundary.

**Deliberate distinction:** comments are public to the series; the session only
decides which of them are marked *"you"*. Watched state is strictly per session.
Both are asserted by tests.

---

### D17 - One container, and every external call proxied by the backend

**Chosen.** A single application container serves the SPA *and* the API on 7777, and
the browser only ever calls `/api/*` on its own origin. The client left both
questions open ("is up to you").

**Rejected:** a separate frontend container, and letting the browser call TVMaze
and the LLM provider directly.

**Why, for the container split.** One artefact, one process, one port, fewer moving
parts in a Jenkins VM — and it is the option that most directly satisfies the stated
requirement.

**Why, for proxying.** The model API keys must never live in the browser; the
insight store, the catalogue TTL cache and the comment threshold are server-side
rules a browser cannot enforce; and a single server-side cache protects the TVMaze
rate limit for all visitors instead of multiplying it per browser.

**Cost.** The backend is on the critical path for content it does not own, and a
frontend-only change requires an image rebuild. In production the split would buy
independent scaling and deploys, and the caching layer would move to a shared store.
Both are recorded in §"If this went to production".

---

## What was deliberately not built

| Not built | Why |
| --- | --- |
| Pagination of comments | 20/50 item previews plus counts are enough; the repository already accepts a `limit`. |
| Real user accounts | Out of scope; the cookie is documented as a stand-in. |
| Rate limiting on our own API | Would be a platform concern (gateway/ingress), not an application one. |
| Background refresh of cached catalogue data | The TTL cache plus per-key locking covers the interactive case. |
| Full observability stack (traces, metrics) | `structlog`-style JSON logs are not in place either; `logging` is used with a container-friendly format and the `/api/health` endpoint exposes enough for a smoke test. Next step if this went to production. |
| Multi-vendor failover for the *catalogue* | TVMaze is the only source the assignment names; the port would make a second source trivial. |

---

## If this went to production

1. **Identity**: replace the cookie with OIDC/session, and move `viewer_id` into the
   token's subject.
2. **Observability**: structured logs with a request id, OpenTelemetry spans around
   the TVMaze and LLM adapters, and metrics for provider success rate and latency -
   the fallback chain already reports who answered, so it converts directly into
   counters.
3. **Caching**: move `AsyncTtlCache` to Redis so the cache survives restarts and is
   shared across replicas; the ports do not change.
4. **Catalogue**: persist shows and episodes locally (nightly sync) to remove the
   upstream dependency from the read path, and keep the gateway port.
5. **Contract**: the client is already generated (D11); the next step is typed,
   error-aware calls and pagination once list endpoints need it.
6. **Delivery**: promote the image by digest, run migrations as a separate job
   rather than in the entrypoint, and add a canary stage.
