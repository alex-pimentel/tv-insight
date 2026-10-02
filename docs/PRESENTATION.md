# Presentation script (30 minutes)

The assignment asks for a **PDF** deck explaining the architecture and the
decisions. This file is the source of that deck: each `##` is one slide, so it can
be exported directly.

```bash
# Export to PDF, pick whichever tool is available:
npx @marp-team/marp-cli docs/PRESENTATION.md -o docs/PRESENTATION.pdf --pdf
pandoc docs/PRESENTATION.md -o docs/PRESENTATION.pdf --pdf-engine=weasyprint
```

Timing, as requested: **10 min** deck · **10 min** live demo · **10 min** peer
review. The deck below is written to be spoken in ten minutes - roughly 45 seconds
per slide.

---

## 1. tv-insight in one slide

* Search TV series on the public TVMaze API, browse episodes by season.
* Mark episodes watched; the state persists. Comment on a series or an episode.
* An **AI insight** for either, behind a provider agnostic interface with a real
  fallback strategy.
* Two containers, one command: `make up` → <http://localhost:7777>.

Measured on the running stack: **380 backend tests**, **98 % coverage without a
database and 99.76 % with PostgreSQL**, `ruff` and `mypy --strict` clean, **95
component tests**, **11 end-to-end tests** in Chromium. Application image:
**321 MB**, Node present only in the build stage.

The behaviours below follow the answers the client gave to six written questions
([`CLIENT-FEEDBACK.md`](CLIENT-FEEDBACK.md)): generation on an explicit action, a
persisted insight regenerated on new comments, and a heuristic fallback.

---

## 2. The one design decision everything follows from

Clean Architecture, four layers, dependency rule enforced by import direction.

```
presentation  →  application  →  domain            (nothing points outward)
infrastructure ─────────────────┘
```

The domain imports **only the standard library**. Verify it in ten seconds:

```bash
grep -rn "^import\|^from" src/tv_insight/domain | grep -v tv_insight
```

*That* is why the domain tests need no database, no HTTP and no fixtures - and why
they run in milliseconds.

---

## 3. What lives where, and what it buys

| Layer | Owns | Buy |
| --- | --- | --- |
| `domain` | invariants, season grouping, watch arithmetic, what an insight may be based on | business rules testable with zero infrastructure |
| `application` | one class per use case, the ports | features are readable as sequences of business steps |
| `infrastructure` | TVMaze adapter, LLM adapters, SQL, composition root | vendors are replaceable and absent from the inner layers |
| `presentation` | HTTP contract, status codes, cookie identity, the SPA | framework lives only at the edge |

---

## 4. Value objects make invalid states unrepresentable

```python
SeriesId(0)            # raises InvalidValue
CommentText("   ")     # raises InvalidValue
Comment(target=SERIES, episode_id=42)   # raises: a series comment has no episode
```

The `Comment` invariant lives in the entity, so no use case has to remember it.
One translation point turns domain errors into application errors, and one module
turns those into HTTP status codes:

```
InvalidValue → InvalidInput → 400      NotFound → ResourceNotFound → 404
ExternalServiceError → 502             ProviderUnavailable → 503
```

---

## 5. Request flow: the detail screen

```
GET /api/series/169
  ├─ TVMaze /shows/169            (TTL cache 300 s)
  ├─ TVMaze /shows/169/episodes   (TTL cache 300 s)
  ├─ SELECT watched_episodes ...  ┐
  ├─ SELECT comments ...          ├─ one transaction (Unit of Work)
  └─ SELECT count(comments) ...   ┘
  ↓
  domain: WatchProgressService → per season and overall progress
  ↓
  one JSON response → one round trip → one loading state → one error state
```

Trade-off: the use case knows about four things, the UI gets one call. See D5 in
`docs/TRADEOFFS.md`.

---

## 6. The AI feature, and why the use case contains no AI

```
GenerateInsight
   ├─ build InsightSubject      (summary, genres, comments)
   ├─ InsightPromptComposer      ← a DOMAIN service: the rule lives in the domain
   └─ provider.generate(request) ← a PORT: the vendor lives outside
```

```
FallbackInsightProvider            the chain, tried on EVERY explicit request
   ├─ HuggingFace    (needs a token)
   └─ heuristic      always available, never fails
```

Decision matrix, in order:

| model providers | stored insight | answer |
| --- | --- | --- |
| answered | any | the fresh answer, persisted as "last known good" |
| failed | exists | the stored answer (`cached`, `degraded`, with a note) |
| failed | empty | the heuristic (`degraded`) |

Adding a vendor is **one class plus one registry line**. No use case, port or test
double changes. Cost control (reuse until N new comments) is one setting away
(`AI_INSIGHT_COMMENT_THRESHOLD`, default `0` = always regenerate).

---

## 7. Failure is a first-class outcome

* `InsightResult` reports `provider`, `degraded`, `cached` and `notes`.
* The UI says *"via heuristic - offline fallback"*. No pretending.
* Vendors are never hammered: 429 is reported immediately and the chain moves on -
  on an interactive screen, degrading fast beats waiting.
* Catalogue retries only transport errors, never a 500 (that is an answer).
* Every upstream error is normalised into an application error inside the adapter,
  so no `httpx` exception ever reaches a use case.

---

## 8. Caching without stampeding

`AsyncTtlCache.get_or_create` takes a **per-key asyncio lock**: 25 concurrent
identical requests trigger **one** upstream call. Asserted in `test_cache.py`.

* Catalogue reads: TTL 300 s - TVMaze is public and rate limited.
* Insights: TTL 900 s keyed on the prompt hash - do not re-bill a model for the same
  question. The Regenerate button bypasses it with `?refresh=true`.

---

## 9. Persistence

```
comments(id PK, viewer_id, target, series_id, episode_id?, text, created_at)
  index (series_id, target, created_at)   -- the series feed
  index (episode_id, created_at)          -- the episode feed

watched_episodes(viewer_id, episode_id) PK   -- idempotent by construction
  index (viewer_id, series_id)               -- the progress query
```

* `timestamptz` everywhere; entities refuse naive datetimes.
* Alembic, applied by the container entrypoint; `alembic check` runs clean in CI.
* One transaction per use case, rolled back automatically on any exception.

---

## 10. One command, two containers

```
docker compose up --build -d          (or simply: make up)

Dockerfile   stage 1  node:22   → npm ci && npm run build
             stage 2  python:3.12-slim
                        entrypoint: alembic upgrade head
                                    uvicorn → :7777
                        non-root user, healthcheck, ~180 MB
```

`depends_on: condition: service_healthy` + a `pg_isready` healthcheck means the app
never races the database. The frontend bundle is served from the same origin as the
API - no CORS in practice, cookies behave.

---

## 11. Testing at four levels

| Level | What it proves | Count |
| --- | --- | --- |
| Domain unit | invariants, grouping, progress, prompt rules, insight freshness | 96 |
| Use case unit | every use case against hand written fakes, including the insight store | 51 |
| Infrastructure unit | mappers, HTTP adapter, cache, provider chain, heuristic, config, composition | 166 |
| Presentation + integration | app factory and lifespan, session, the real ASGI contract, real PostgreSQL repositories | 55 |
| System / E2E | the built bundle in Chromium against the real API and database | 11 |

Fakes implement the real ports, so a port change breaks the suite instead of
rotting silently. The E2E suite runs in the official Playwright image, so a Jenkins
VM needs no browser installation.

---

## 12. Live demo (10 minutes)

1. `make clean && make up` - one command, then the health badge in the header shows
   `db up · ai heuristic`.
2. Search *"breaking bad"* - async results with poster, year, genres.
3. Open the series: summary, genres, seasons with progress bars, **62 episodes**.
4. Expand a season, tick an episode - the progress bar moves instantly.
5. **Reload the page** - the episode is still ticked.
6. Open the AI panel in its **idle** state: nothing has been requested yet. Press
   **View insights**. Show the provenance footer: provider, "offline fallback",
   "based on N comments".
7. Press **Regenerate** - a new answer arrives, because every explicit request
   reaches the provider.
8. Stop the tokens (`HUGGINGFACE_API_TOKEN= docker compose up -d`) and press
   **View insights** again: the panel now says **reused** and explains in the
   payload that the model was unreachable, serving the last stored answer. Ask for
   an insight on a series that has none and the heuristic answers instead.
9. Restore the token, press **guest session · new** in the header, reload - watched
   state is gone, comments remain but are no longer marked as yours.
10. `make logs` - show that the fallback notes record *why* a provider was skipped,
    and that no secrets are logged.
11. `curl localhost:7777/api/health` - providers, availability and the configured
    model for each.
12. Stop the `db` container and reload: the UI shows a clear error, the process
    stays up, `/api/health` reports `degraded`.

---

## 13. Peer review: the five files to read

1. `infrastructure/composition.py` - the entire object graph in one place.
2. `domain/entities/guide.py` - pure business logic (`seasons()`).
3. `application/use_cases/generate_insight.py` - the AI feature with no AI in it.
4. `infrastructure/ai/fallback.py` - the fallback composite.
5. `tests/integration/test_api.py` - the contract, end to end, in process.

---

## 14. Questions to expect

**"Why four layers for such a small scope?"**

Because the scope is small, the architecture must be justified by testability, not
size. The exception is documented as D1.

**"Show me what you would change if this went to production."**

`docs/TRADEOFFS.md` §"If this went to production": OIDC instead of the cookie,
OpenTelemetry around both adapters, Redis for the cache, a local catalogue sync,
OpenAPI-generated TypeScript, and migrations as a separate job rather than in the
entrypoint.

**"Is the rule based provider cheating?"**

No, it is the last tier of a fallback chain, and it is honest: the response marks
itself `degraded` and explains itself in `notes`. It exists so the feature is
demonstrable where no credentials exist - which is the requirement, not a shortcut.
When a token is present, HuggingFace or OpenRouter answers first.

**"Why not generate the frontend types from OpenAPI?"**

Nine stable response models; a hand written client is readable and needs no build
step. It is listed as the first thing to automate (D11).

**"How do you know the migration matches the models?"**

`alembic check` runs in CI and in the pipeline, and reports "no new upgrade
operations detected".

**"What happens if a user marks an episode of another series?"**

`SetEpisodeWatched` resolves the episode inside the series guide before writing, so
it answers 404 and no row is created (test: `test_episode_from_another_series_is_refused`).
