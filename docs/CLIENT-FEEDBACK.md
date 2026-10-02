# Client feedback → implementation

This file records the answers received from the recruiter about the assignment and
what each one changed in the code. It exists so the decisions can be traced to the
person who made them, and so the presentation can quote them.

Every row links to the file that implements it. Where the answer required a change,
the "before" is stated so the delta is visible.

---

## Answer 1 — "Every time users click on a 'View Insights' button"

**Question was:** fire insights generation on every show/episode view, or on an
explicit button?

**Decision:** explicit user action.

**Before:** `InsightPanel` fetched the insight on mount (`useEffect`), so opening a
details page triggered a model call whether the user wanted it or not.

**Now:**

* The panel renders an idle state with a **View insights** button and an
  explanation of what the insight is built from. Nothing is requested on mount.
* Once shown, the panel offers **Regenerate**, which asks for a fresh answer
  (`?refresh=true`) and bypasses the optional reuse window.
* Navigating to another subject returns the panel to idle; it never self-fetches.

**Where:** `frontend/src/components/InsightPanel.tsx`,
`frontend/src/pages/SeriesPage.tsx`, `frontend/src/pages/EpisodePage.tsx`.
Covered by component tests (`pages.test.tsx` → *"does not call the model until the
user asks for it"*) and by E2E (`journey.spec.ts` → *"the insight is generated on
demand"*).

**Consequence worth mentioning:** generation is now user-driven, so the cost is
bounded by intent rather than by page views. The `AI_INTEGRATION` criteria for
"graceful failure" and the FinOps argument both get stronger.

---

## Answer 2 — "Perfect, but as a simple test, consider 1 comment is enough"

> **Amendment (after the first delivery).** The team later reversed the default:
> generation must be attempted on **every** explicit request, with the stored
> insight used as the *failure* fallback rather than as a cost cache. The
> threshold is therefore **0 by default** (0 = always regenerate) and the
> client's rule remains one setting away (`AI_INSIGHT_COMMENT_THRESHOLD=1`).
> The mechanism below is unchanged; only the default flipped. See the decision
> matrix at the end of this file.

**Question was:** cache the insight and only regenerate when X new comments exist
(summary and genres rarely change).

**Decision:** implement the rule, threshold configurable, **default 0 = regenerate
on every request**.

**Before:** the insight was cached in process, keyed by a hash of the prompt, with a
15-minute TTL. Nothing was persisted and there was no notion of "the input
changed", so a restart or a TTL expiry meant paying again.

**Now:** the insight is **persisted** together with the number of comments it was
built from, and the reuse window is expressible:

```
comments at generation time = N   →   stored.based_on_comment_count = N
current comments = M
threshold = 0  →  never reuse: regenerate on every request   (default)
threshold = 1  →  M - N < 1  →  serve the stored insight, no provider call
                  M - N >= 1 →  regenerate and store again
```

The rule lives in the domain (`StoredInsight.is_fresh_for`) because it is a business
rule, not a caching detail. Counts are monotonic (comments are only ever added), so
the rule needs no clock.

**Where:**

| Piece | File |
| --- | --- |
| The rule | `backend/src/tv_insight/domain/entities/insight.py` |
| The use case that applies it | `backend/src/tv_insight/application/use_cases/generate_insight.py` |
| The port | `backend/src/tv_insight/domain/ports/repositories.py` (`InsightRepository`) |
| The table | `backend/src/tv_insight/infrastructure/db/models.py` (`InsightRow`) |
| The migration | `backend/migrations/versions/0002_insights.py` |
| The threshold setting | `AI_INSIGHT_COMMENT_THRESHOLD` (default `0`) |

**Visible to the user:** the panel shows *"based on N comments"* and, when new
comments arrived since generation, *"N new comments since this insight"* — so the
rule is demonstrated, not just implemented.

**Deliberate choices and their reasons:**

* The baseline is *the number of comments actually fed to the model*. For an episode
  with no comments yet we feed the series conversation, so the baseline is the
  series count. That keeps the comparison honest even when the input source shifts.
* `Regenerate` sends `?refresh=true`, which bypasses the reuse window when it is
  enabled.

---

## Answer 3 — "The idea is to create a heuristic process"

**Question was:** for the fallback strategy, should we retry with another
model/provider, show a saved insight, or show "service unavailable"?

**Decision:** a **heuristic process** — a deterministic, local rule-based
generation from data we already hold.

**Interpretation applied (and worth confirming in the presentation):** the client
prefers a local heuristic over paying for a second model tier. So the default chain
is now:

```
huggingface  →  heuristic        (default)
huggingface  →  openrouter  →  heuristic   (opt-in, via AI_PROVIDER_ORDER)
```

Provider independence is still demonstrated (any tier can be inserted by
configuration; the registry is the only place that names vendors), but the *costly*
second tier is not paid for by default.

**Before:** the terminal provider was called `RuleBasedInsightProvider` and its
output mentioned genres, a summary excerpt and the first comment.

**Now:** renamed to `HeuristicInsightProvider` and made a genuine heuristic:

* genres, and an audience hint derived from the primary genre;
* a truncated summary excerpt;
* **community signal**: it looks for words that appear in more than one comment and
  reports them as recurring themes ("2 community comments keep returning to
  \"pacing\""), falling back to a quoted example when nothing repeats.

It stays honest: `provider: "heuristic"` and `degraded: true` on the answer, and
the UI labels it *"offline fallback"*.

**Where:** `backend/src/tv_insight/infrastructure/ai/heuristic.py`,
`backend/src/tv_insight/infrastructure/ai/factory.py`.

**Also implemented from the same answer — "show the saved Insight":** if
generation fails (or returns nothing) and a stored insight exists, the stored one is
served, marked degraded, with a note explaining why. Only when there is no stored
insight does the request fail with `503 ProviderUnavailable`. That is the third
option in the question, kept as a last resort behind the heuristic.

**Trade-off accepted:** a heuristic cannot understand meaning. It only claims a
theme when a word repeats, and it says so in its own `notes`. It is a fallback, not
a feature pretending to be an LLM.

---

## Answer 4 — "Some use as guest, ou use the session"

**Question was:** do we need a registration interface, or is seeding three users
with an account switcher enough?

**Decision:** guest, carried by a session. No registration, no seeded accounts.

**Already in place:** a `httpOnly`, `SameSite=Lax` cookie holding an opaque guest
identifier, minted by the first endpoint that needs it.

**Added as a result of the answer:**

* `GET /api/session` — reports `{"kind": "guest"}` without exposing the identifier
  (the cookie is `httpOnly` on purpose).
* `POST /api/session/reset` — discards the current guest identity, so a fresh one is
  minted on the next request. In a demo this makes the session scoping visible:
  watched state resets; public comments remain but are no longer marked as "yours".
* A **guest session · new** affordance in the header.

**Where:** `backend/src/tv_insight/presentation/api/routers/session.py`,
`backend/src/tv_insight/presentation/api/dependencies.py` (`get_viewer_id`),
`frontend/src/App.tsx`.

**Explicitly not built:** registration, password reset, account switching, social
login. Documented as out of scope (decision D7 in `docs/TRADEOFFS.md`).

**Note on scope of the session:** comments are public to the series (everyone sees
the conversation); the session only decides which ones are marked *"you"*. Watched
state is strictly per session. This distinction is asserted by
`test_a_reset_session_does_not_see_previous_state`.

---

## Answer 5 — "Is up to you" (one container serving the UI + API, or split?)

**Decision:** a **single container** that serves both, which is the simplest option
that satisfies the requirement (*"one container for the application, one for the
database, on port 7777"*).

**Why this is the better of the two "up to you" options here:**

* one artefact, one process, one port to expose — fewer moving parts in a Jenkins
  VM and a smaller surface for the reviewer to reason about;
* same-origin for the SPA and the API, so the guest cookie behaves identically in
  development and production and no CORS policy has to be maintained;
* the FastAPI process already owns the HTTP layer, so serving static files from it
  costs nothing operationally;
* the split (a separate frontend container) would buy independent scaling and
  independent deploys, neither of which is needed at this scope.

**Where:** `Dockerfile` (multi-stage: Node builds the SPA, the Python image serves
it), `backend/src/tv_insight/presentation/app.py` (`_mount_frontend`), and
`STATIC_DIR` as the only configuration point.

**Trade-off:** the SPA and the API scale together, and a frontend-only change still
requires an image rebuild. Both are acceptable here and both are listed in
`docs/TRADEOFFS.md` as the things a production split would address.

---

## Answer 6 — "Is up to you" (frontend calls the external API directly, or through the backend?)

**Decision:** **everything goes through the backend.** The browser only ever talks
to `/api/*` on the same origin.

**Why:**

1. **Secrets.** The model API keys would otherwise have to live in the browser.
   With a pure frontend the LLM integration would be impossible to do safely.
2. **Cost control and caching.** The insight store, the catalogue TTL cache and the
   comment-threshold rule all live server-side; the browser cannot enforce them.
3. **Unified error vocabulary.** A single mapping from `ApplicationError` to status
   code, and a single place to log upstream failures.
4. **Rate limiting.** TVMaze is a public, rate limited API; one server-side cache
   protects the budget for every visitor, whereas direct browser calls multiply it.
5. **Identity.** The guest session cookie is `httpOnly` and read server-side.

**Where:** the SPA has exactly one network entry point,
`frontend/src/api/client.ts`; there is no other `fetch` in the frontend (enforced by
review, and every test stubs that single helper).

**Trade-off:** the backend is on the critical path for content it does not own, so
it must be fast and resilient — which is what the TTL cache, the retry policy and
the graceful degradation are for.

---

## Summary table

| # | Question | Client answer | Status | Implementation |
| - | --- | --- | --- | --- |
| 1 | When to generate insights | On the "View Insights" button | **Implemented** | `InsightPanel.tsx` idle state + explicit action |
| 2 | Regeneration threshold | Cache it; 1 comment is enough | **Implemented, default reversed to 0** | `StoredInsight.is_fresh_for` + `insights` table; `AI_INSIGHT_COMMENT_THRESHOLD=1` restores the rule |
| 3 | Fallback strategy | A heuristic process | **Implemented, order refined** | `HeuristicInsightProvider`; model → stored answer → heuristic |
| 4 | Registration or guest? | Guest / session | **Implemented** | `GET /api/session`, `POST /api/session/reset`, header affordance |
| 5 | One container or split? | Up to us | **Decided** | Single container, multi-stage; documented rationale |
| 6 | Direct API calls or proxy? | Up to us | **Decided** | Everything through the backend; documented rationale |

---

## The insight decision matrix (current behaviour)

This is the single source of truth for what a click does. It supersedes the earlier
"reuse while fresh" default.

| Model providers | Stored insight | Result |
| --- | --- | --- |
| answer | any | the fresh answer is returned **and persisted** (last known good) |
| fail | exists | the stored answer is returned, flagged `cached` + `degraded`, with a note |
| fail | empty | the heuristic answers, flagged `degraded`; nothing is persisted |

Two rules make this safe:

* **Only model answers are persisted.** A heuristic can never overwrite a good
  insight in the store, which is what allows rule 2 to prefer it over a freshly
  composed fallback.
* **The reuse window is opt-in.** `AI_INSIGHT_COMMENT_THRESHOLD` defaults to `0`
  (regenerate every time) and the in-process cache TTL defaults to `0` (no
  memoisation), so "generate" really means "call the provider".

Evidence: `backend/tests/unit/application/test_insight_store.py` covers all three
rows, `backend/tests/unit/domain/test_stored_insight.py` covers the threshold
semantics, and `frontend/e2e/journey.spec.ts` exercises rows 1 and 2 against the
running stack with a real provider.

---

## What this changed in the architecture

Two of the answers moved responsibilities across layers, which is worth calling out
in the presentation because it shows the architecture bending without breaking:

1. **A new aggregate (`StoredInsight`) and a new port (`InsightRepository`).**
   The freshness rule is domain logic; persistence of the insight is an adapter.
   The `UnitOfWork` gained a third repository, and the API contract gained
   `based_on_comment_count`.
2. **`CommentTarget` was promoted to `ContentTarget` and moved to
   `domain/value_objects.py`.** Once the insight aggregate needed the same
   "series | episode" vocabulary, keeping a second, identical enum would have been
   duplication. One value object, shared by both aggregates.

Neither change touched the provider chain, the TVMaze adapter or the existing use
cases beyond the insight one — which is the point of having ports.

---

## Points to confirm with the client

These are the assumptions that were reasonable to make but are worth stating out
loud in the presentation:

1. **Generation on every click vs. the cost rule.** The team chose "generate on
   every request" (threshold `0`). The client's cost-control rule is one setting
   away (`AI_INSIGHT_COMMENT_THRESHOLD=1`). Worth confirming which one the client
   wants for the demo, because they affect LLM spend directly.
2. **Heuristic vs second provider.** The answer chose the heuristic. The
   implementation keeps a second model tier available but disabled by default. If
   the client wants it on, it is one environment variable.
3. **Order of the failure fallbacks.** Model → stored answer → heuristic. The client
   listed both "show the saved insight" and "heuristic process"; the implementation
   prefers the saved insight because the store only holds real model answers, and
   falls back to the heuristic only when there is nothing stored.
4. **Deleting comments.** There is no delete endpoint, so the comment count is
   monotonic and the rule needs no clock. If deletion is added, the count could go
   down; `is_fresh_for` already treats that as "never fresh".
5. **Comments are public.** They are not filtered by session; the session only marks
   authorship. That was implied by "users can leave comments on a series or an
   episode" without any notion of privacy, but it is a product decision worth
   confirming.
