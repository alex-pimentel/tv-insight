# Architecture

This document explains how `tv-insight` is put together, why it is put together
that way, and what each boundary buys us. Code references use
`path:LNN` so they can be opened directly.

---

## 1. The problem and the shape of the solution

The assignment asks for a module that will be "a technical reference for future
teams", with a limited scope but real architectural weight:

* read a public catalogue over HTTP (TVMaze),
* persist user state (watched episodes, comments),
* integrate an LLM behind a robust boundary,
* run as two containers on a fixed port, started by one command,
* and demonstrate SOLID, Clean Code, design patterns and modern architecture.

The natural answer for "limited scope, high architectural expectations" is Clean
Architecture: put the business rules at the centre, express every external
dependency as a port, and implement the ports at the edge. The scope is small, so
the layering has to pay for itself immediately rather than as a future promise -
which is why the tests are structured around the same boundaries.

---

## 2. Layers and the dependency rule

```
                       ┌─────────────────────────────────────────────┐
   HTTP / browser ───► │  presentation     FastAPI routers, schemas  │
                       │                   static SPA, error mapping │
                       └────────────────────┬────────────────────────┘
                                            │ depends on
                       ┌────────────────────▼────────────────────────┐
                       │  application      use cases, ports, DTOs    │
                       │                   transaction boundary      │
                       └────────────────────┬────────────────────────┘
                                            │ depends on
                       ┌────────────────────▼────────────────────────┐
                       │  domain           entities, value objects,  │
                       │                   repository ports,          │
                       │                   domain services            │
                       │                   (standard library only)    │
                       └─────────────────────────────────────────────┘
                                            ▲
                                            │ implements
                       ┌────────────────────┴────────────────────────┐
                       │  infrastructure   TVMaze adapter, LLM        │
                       │                   adapters, SQLAlchemy,      │
                       │                   composition root           │
                       └─────────────────────────────────────────────┘
```

The rule is enforced by direction of imports, and it is easy to verify by hand:

```bash
# domain must not know about anything we did not write
grep -rn "^import\|^from" backend/src/tv_insight/domain | grep -v "tv_insight\." | grep -v "__future__"
```

`domain/` imports only the standard library. That is not a slogan: it is what
makes `tests/unit/domain` run in milliseconds with no fixtures, no network and no
database.

### What each layer owns

| Layer | Owns | Explicitly does **not** own |
| --- | --- | --- |
| `domain` | Invariants, the `Comment`/`WatchedEpisode` concepts, season grouping, watch arithmetic, what an insight may be based on | Persistence, HTTP, prompts-for-vendors, JSON shapes |
| `application` | One class per use case, orchestration, transactions, the repository/LLM/catalogue **ports** | Vendor details, SQL, status codes |
| `infrastructure` | Adapters implementing the ports, the composition root, caching, retries | Business rules |
| `presentation` | HTTP contract, status code mapping, cookie identity, serving the SPA | Business rules, persistence |

---

## 3. Domain model

```
Series(id, name, summary, genres[], premiered, status, poster, rating, ...)
Episode(id, series_id, name, season, number, summary, airdate, runtime, image)
  └── EpisodeGuide(series_id, episodes[])  ── groups into ──►  Season(number, episodes[])
Comment(id, viewer_id, target ∈ {SERIES, EPISODE}, series_id, episode_id?, text, created_at)
WatchedEpisode(viewer_id, series_id, episode_id, watched_at)
```

* **Value objects** (`domain/value_objects.py`) validate on construction:
  `SeriesId(0)` and `CommentText("  ")` cannot exist. Invalid states are
  unrepresentable rather than "checked somewhere later".
* **`Comment` carries an invariant**: an episode comment must reference an
  episode, a series comment must not. It is enforced in `comments.py:49`, so no
  use case has to remember the rule.
* **Text normalisation is domain knowledge.** TVMaze returns HTML inside
  summaries; `domain/text.py` strips it, so the API never leaks `<p>` tags and the
  domain never depends on an HTML library.
* **`EpisodeGuide.seasons()`** (`guide.py:51`) is the grouping rule: specials
  (season 0) last, episodes ordered. Pure function, covered by focused unit tests.
* **`WatchProgressService`** (`services/watch_progress.py`) computes per-season and
  overall progress from a guide and a set of watched ids. Arithmetic in the domain,
  not in a SQL aggregate or a React component.
* **`InsightPromptComposer`** (`services/insight_prompt.py`) encodes the business
  rule *"an insight is derived from the summary, the genres and the user comments,
  and must stay short, and must not invent plot"*. It is a domain service because
  it is a rule, not a vendor concern.

---

## 4. Ports and adapters

Every dependency crossing a boundary is an abstract class owned by the inner layer.

| Port | Declared in | Implemented by | Faked in tests by |
| --- | --- | --- | --- |
| `TvMazeGateway` | `application/ports/tvmaze.py` | `HttpTvMazeGateway` | `InMemoryTvMazeGateway` |
| `InsightProvider` | `application/ports/insight.py` | HuggingFace, OpenRouter, rule based, fallback, caching | `ScriptedInsightProvider`, `UnavailableInsightProvider` |
| `UnitOfWork` | `application/ports/persistence.py` | `SqlAlchemyUnitOfWork` | `InMemoryUnitOfWork` |
| `CommentRepository` | `domain/ports/repositories.py` | `SqlCommentRepository` | `InMemoryCommentRepository` |
| `WatchedEpisodeRepository` | `domain/ports/repositories.py` | `SqlWatchedEpisodeRepository` | `InMemoryWatchedEpisodeRepository` |
| `Clock` | `application/ports/clock.py` | `SystemClock` | `FixedClock` |

Repository ports live in the **domain** because the domain owns the persistence
*contract* it needs; the SQL implementation lives in infrastructure. That is the
inversion that makes the dependency arrow point inwards.

`Clock` exists for one practical reason: tests assert that newer comments come
first and that `watched_at` is recorded, without sleeping.

---

## 5. Request flows

### 5.1 Series detail (one round trip instead of four)

```
GET /api/series/169
  │
  ├─ presentation  get_series_detail(container, viewer_id, series_id)
  │     └─ viewer_id comes from the httpOnly cookie; minted on first use
  │
  ├─ application   GetSeriesDetails.execute(169, viewer)
  │     ├─ gateway.get_series(169)          ─► TVMaze /shows/169      (TTL cached)
  │     ├─ gateway.get_episodes(169)        ─► TVMaze /shows/169/episodes (TTL cached)
  │     └─ async with uow:
  │            uow.watches.list_episode_ids(viewer, 169)   ─► SELECT … watched_episodes
  │            uow.comments.list_for_series(169, limit)    ─► SELECT … comments
  │            uow.comments.count_for_series(169)          ─► SELECT count(*)
  │
  ├─ domain        WatchProgressService.summarize(guide, watched)
  │                 → per season {watched,total,ratio} and overall ratio
  │
  └─ presentation  SeriesDetail → SeriesDetailModel → JSON
```

Four UI needs are served by one HTTP call. The cost is that `GetSeriesDetails`
knows about all of them; the benefit is one round trip, one loading state, one
error state in the UI. See `docs/TRADEOFFS.md` §"Aggregate on the server".

### 5.2 Marking an episode as watched

```
PUT /api/series/169/episodes/12192/watched  {"watched": true}
  │
  ├─ SetEpisodeWatched.execute(...)
  │     ├─ gateway.get_episodes(169)  ─► served from cache: the write is validated
  │     │                                against the real guide, so a watched row
  │     │                                can never point at another series
  │     └─ async with uow: uow.watches.save(WatchedEpisode(...)); commit()
  │
  └─ 200 {"watched": true}
```

The composite primary key `(viewer_id, episode_id)` makes marking idempotent in the
database itself, not in application code.

### 5.3 AI insight - explicit generation, a stored safety net, and the chain

```
GET /api/series/169/insight         (the UI only calls this after "View insights")
  │
  ├─ GenerateInsight.for_series(169, refresh=False)
  │     ├─ series := gateway.get_series(169)
  │     ├─ async with uow:
  │     │     current_count := count_for_series(169)
  │     │     stored        := uow.insights.get(SERIES, 169)
  │     │     optional reuse window: only when the threshold is > 0
  │     │     (default 0 = regenerate on every request)
  │     ├─ subject := InsightSubject(SERIES, title, summary, genres, comments)
  │     ├─ prompt  := InsightPromptComposer.compose(subject)      ← domain rule
  │     └─ provider.generate(InsightRequest(prompt, subject))     ← always tried
  │            └─ FallbackInsightProvider
  │                 ├─ HuggingFaceInsightProvider  (needs a token)
  │                 └─ HeuristicInsightProvider    (always available)
  │
  └─ decision matrix:
       1. a model answered        → persist it (last known good) and return it
       2. chain fell to heuristic → return the stored model answer instead, if any
       3. nothing answered at all → the stored answer, else ProviderUnavailable
```

* **Generation is explicit.** The panel does not call this on mount; it is the
  *View insights* button.
* **The store is the last known good answer, not a general cache.** Only answers
  produced by a real model are persisted, so a heuristic can never overwrite a good
  insight. That is what makes rule 2 safe.
* **Rules 2 and 3 are what the ``stored``/``degraded`` flags in the response mean.**
  The UI renders them: *"reused"* for the stored answer, *"offline fallback"* for
  the heuristic.
* **Cost control is configurable, not removed.** `AI_INSIGHT_COMMENT_THRESHOLD`
  (default `0`) enables the "reuse until N new comments" window that the client
  originally asked for; `AI_INSIGHT_CACHE_TTL_SECONDS` (default `0`) re-enables the
  in-process burst cache. Both are off by default because the product wants a fresh
  generation per click.
* **Provenance is part of the contract**: `provider`, `degraded`, `cached`,
  `based_on_comment_count` and `notes` all travel to the UI.
* **The use case still holds no AI knowledge.** Adding a vendor is a class plus one
  registry line in `ai/factory.py`.

---

## 6. Application of SOLID

| Principle | Where it shows |
| --- | --- |
| **S**ingle responsibility | `SearchSeries` searches; `GenerateInsight` composes and delegates; `SqlCommentRepository` only speaks SQL. Mapping lives in `application/mappers.py`, prompt building in a domain service. |
| **O**pen/closed | Adding an AI vendor is a new class plus one line in `ai/factory.py:31`. No use case, port or test double changes. Adding a comment target means a new `CommentTarget` member and a validation branch. |
| **L**iskov | `CachingTvMazeGateway` and `CachingInsightProvider` are drop-in decorators: same contract, added behaviour. Tests exercise the fakes and the real implementations against the same ports. |
| **I**nterface segregation | Four small ports instead of one "repository service". `TvMazeGateway` has three read methods; `Clock` has one. |
| **D**ependency inversion | `application` and `domain` declare the abstractions; `infrastructure` implements them. Nothing inner imports `httpx` or `sqlalchemy`. |

---

## 7. Persistence

Two tables; the SQLAlchemy models are *persistence* models, deliberately not the
domain entities. Repositories translate in both directions
(`infrastructure/db/repositories.py:32`).

```
comments
  id           varchar(64)  PK
  viewer_id    varchar(64)  idx
  target       varchar(16)          'series' | 'episode'
  series_id    integer      idx
  episode_id   integer      idx NULL
  text         text
  created_at   timestamptz  idx
  index (series_id, target, created_at)   -- the series comment feed
  index (episode_id, created_at)          -- the episode comment feed

watched_episodes
  viewer_id    varchar(64)  PK ┐
  episode_id   integer      PK ┘   idempotent by construction
  series_id    integer      idx
  watched_at   timestamptz
  index (viewer_id, series_id)            -- the progress query
```

* `ix_comments_series_target_created` serves the series feed directly; without it
  the query would sort the whole table for a single series.
* Timestamps are `timestamptz` and the entities refuse naive datetimes
  (`comments.py:41`), so ordering is unambiguous across time zones.
* Schema changes go through Alembic (`backend/migrations/`), applied by the
  container entrypoint before the process starts. `alembic check` runs clean, which
  is asserted in the pipeline.

**Why a transaction per use case?** `SqlAlchemyUnitOfWork`
(`infrastructure/db/unit_of_work.py`) opens one session, exposes the repositories
and rolls back automatically if an exception escapes the `async with`. A write use
case therefore either lands completely or not at all, and the use case never sees
a session.

---

## 8. Resilience and caching

| Concern | Implementation | Why |
| --- | --- | --- |
| Transient catalogue failures | `retrying_call` (`infrastructure/resilience.py`) retries only transport errors, twice with exponential backoff | A 500 from TVMaze is an answer, not a hiccup; do not hammer it |
| Rate limits | 429 is reported immediately as `ProviderUnavailable` | In an interactive screen, degrading fast beats waiting |
| Repeated catalogue reads | `CachingTvMazeGateway` + `AsyncTtlCache` (TTL 300 s) | TVMaze is a public, rate limited API; the same show is fetched on every interaction |
| Cache stampede | Per-key `asyncio.Lock` inside `AsyncTtlCache.get_or_create` | 25 concurrent identical requests trigger **one** upstream call (asserted in `test_cache.py`) |
| Repeated insights | `CachingInsightProvider` keyed on the prompt hash (TTL 900 s) | Avoids re-billing a paid model for the same question |
| Vendor outage | `FallbackInsightProvider` + terminal rule based provider | The feature degrades instead of disappearing |

Every upstream failure is normalised into an application error inside the adapter
(`client.py:_get_json`), so no `httpx` exception ever reaches a use case.

---

## 9. Error taxonomy

```
DomainError
├── InvalidValue      → application.translated_domain_errors → InvalidInput      → 400
└── NotFound          →                                       ResourceNotFound   → 404

ApplicationError
├── InvalidInput                                                                 → 400
├── ResourceNotFound                                                             → 404
├── ExternalServiceError   (catalogue down, malformed payload)                   → 502
└── ProviderUnavailable    (every AI tier failed)                                → 503
```

`presentation/api/errors.py` is the only module that knows about status codes. The
single translation point between domain and application vocabulary is
`translated_domain_errors()` (`application/errors.py:36`), which keeps value
objects free to raise domain errors while the edge only handles application ones.

---

## 10. Frontiers of the SPA

* One origin. FastAPI serves the built bundle and the API; the Vite dev server
  proxies `/api`. No CORS in practice, no cookie gymnastics in the browser.
* The viewer identity is an `httpOnly`, `SameSite=Lax` cookie minted by the first
  endpoint that needs it (`presentation/api/dependencies.py:29`). Not a security
  boundary - a pragmatic stand-in for a session, documented as such.
* The frontend keeps its own progress arithmetic (`frontend/src/lib/progress.ts`)
  so a checkbox flips instantly; the server remains the source of truth on the next
  load, and a failed write reloads and re-renders (covered by a component test).
* `presentation/api/schemas.py` is the API contract and is independent from the
  application DTOs: the use cases can change shape without breaking the browser.

---

## 11. Configuration and start-up

```
docker compose up
  ├── db      postgres:16-alpine, healthcheck pg_isready
  └── app     waits for db healthy
               ├── entrypoint: alembic upgrade head
               └── uvicorn (create_app → Settings → Container.build)
```

`Container.build` (`infrastructure/composition.py:85`) is the composition root and
can be read top to bottom as the dependency graph. Because it is injectable into
`create_app`, the integration suite mounts the **same application** with in-memory
fakes and no network, no database and no LLM.

Configuration is a single validated `Settings` object; no module reads
`os.environ` on its own.

---

## 12. Where to look first

1. `backend/src/tv_insight/infrastructure/composition.py` - the whole graph.
2. `backend/src/tv_insight/domain/entities/guide.py` - the pure business logic.
3. `backend/src/tv_insight/application/use_cases/generate_insight.py` - the AI
   feature with no AI knowledge in it.
4. `backend/src/tv_insight/infrastructure/ai/fallback.py` - the fallback strategy.
5. `backend/tests/integration/test_api.py` - the contract, end to end in-process.
6. `docs/TRADEOFFS.md` - what was deliberately not done.
