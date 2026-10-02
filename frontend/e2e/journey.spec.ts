import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * Full user journey through the built UI.
 *
 * The catalogue and the LLM are stubbed at the network edge so the assertions are
 * about *our* behaviour - rendering, explicit insight generation, optimistic
 * updates, persistence through the real API and the guest session - rather than
 * about TVMaze being reachable.
 *
 * Comments are global to a series (the session only marks which ones are "mine"),
 * so each test uses its own series id to stay independent when running in
 * parallel.
 */

function seriesCard(id: number, name: string) {
  return {
    id,
    name,
    year: 2008,
    poster_url: null,
    poster_thumbnail_url: null,
    genres: ["Drama", "Crime"],
    status: "Ended",
    rating: 9.2,
    network: "AMC",
    language: "English",
  };
}

function episode(id: number, season: number, number: number): Record<string, unknown> {
  return {
    id,
    name: `Episode ${number}`,
    season,
    number,
    code: `S${String(season).padStart(2, "0")}E${String(number).padStart(2, "0")}`,
    summary: `Summary ${number}`,
    airdate: "2008-01-20",
    runtime_minutes: 47,
    image_url: null,
    watched: false,
  };
}

const FIRST_EPISODE_ID = 1001;

function detail(id: number, seasonOneEpisodes: number[] = [1, 2]) {
  return {
    series: seriesCard(id, `Series ${id}`),
    summary: "A chemistry teacher turns to crime.",
    seasons: [
      {
        number: 1,
        label: "Season 1",
        watched: 0,
        total: seasonOneEpisodes.length,
        progress: 0,
        episodes: seasonOneEpisodes.map((number) =>
          episode(FIRST_EPISODE_ID + number - 1, 1, number),
        ),
      },
    ],
    watched: 0,
    total_episodes: seasonOneEpisodes.length,
    progress: 0,
    comment_count: 0,
    comments: [],
  };
}

function insight(id: number) {
  return {
    text: "A slow burning character study for fans of crime drama.",
    provider: "heuristic",
    degraded: true,
    cached: false,
    generated_at: "2024-01-01T12:00:00Z",
    target: "series",
    target_id: id,
    based_on_comment_count: 1,
    notes: ["huggingface: skipped, not configured"],
  };
}

/** Stubs only the catalogue endpoints; comments and watched stay real. */
async function stubCatalogue(
  page: Page,
  id: number,
  totalEpisodes = 2,
): Promise<void> {
  const body = detail(id, Array.from({ length: totalEpisodes }, (_, i) => i + 1));
  await page.route("**/api/series/search**", (route) =>
    route.fulfill({
      json: { query: "series", count: 1, results: [seriesCard(id, `Series ${id}`)] },
    }),
  );
  await page.route(`**/api/series/${id}/insight**`, (route) =>
    route.fulfill({ json: insight(id) }),
  );
  await page.route(`**/api/series/${id}`, (route) => route.fulfill({ json: body }));
}

test("search, open a series, ask for an insight, comment and mark an episode watched", async ({
  page,
}) => {
  await stubCatalogue(page, 101);

  await page.goto("/");
  await page.getByLabel(/find a tv series/i).fill("series");
  await expect(page.getByTestId("series-card")).toHaveCount(1);

  await page.getByRole("link", { name: /series 101/i }).click();
  await expect(page.getByTestId("series-title")).toHaveText("Series 101");
  await expect(page.getByTestId("overall-progress")).toContainText("0 of 2 episodes");

  // Generation is explicit: nothing is requested until the user asks for it.
  await expect(page.getByTestId("insight-text")).toHaveCount(0);
  await page.getByRole("button", { name: /view insights/i }).click();

  await expect(page.getByTestId("insight-text")).toContainText("slow burning");
  await expect(page.getByTestId("insight-provider")).toContainText("heuristic");
  await expect(page.getByTestId("insight-basis")).toContainText("comment");

  // Comment on the series.
  await page.getByLabel(/your comment/i).fill("Best show ever");
  await page.getByRole("button", { name: /post comment/i }).click();
  await expect(page.getByTestId("comment-item").first()).toContainText("Best show ever");

  // Mark the first episode as watched and see progress update.
  await page.getByLabel("Mark S01E01 Episode 1 as watched").check();
  await expect(page.getByTestId("overall-progress")).toContainText("1 of 2 episodes");
});

test("the panel distinguishes a fresh answer from a reused one", async ({ page }) => {
  const id = 102;
  // The UI contract: `cached` means "served from the store". The backend decides
  // when that happens (see the matrix in docs/CLIENT-FEEDBACK.md); this test pins
  // the two states the panel must render.
  await page.route(`**/api/series/${id}/insight**`, async (route) => {
    const refresh = route.request().url().includes("refresh=true");
    await route.fulfill({
      json: { ...insight(id), cached: !refresh },
    });
  });
  await page.route(`**/api/series/${id}`, (route) =>
    route.fulfill({ json: detail(id) }),
  );

  await page.goto(`/series/${id}`);

  // A normal request in this stub is reported as reused.
  await page.getByRole("button", { name: /view insights/i }).click();
  await expect(page.getByTestId("insight-cached")).toContainText("reused");

  // Regenerating asks for a fresh answer, so the badge disappears.
  await page.getByRole("button", { name: /regenerate/i }).click();
  await expect(page.getByTestId("insight-cached")).toHaveCount(0);
});

/**
 * A real catalogue subject.
 *
 * Watched state and comments live against a *real* series, because the backend
 * validates the episode against the catalogue before writing. When the public API
 * is unreachable these two tests skip instead of failing - the rest of the suite
 * stays hermetic.
 */
const REAL_SERIES_ID = 169; // Breaking Bad, stable on TVMaze

async function realSeries(
  page: Page,
): Promise<{ episodeId: number; episodeCount: number } | null> {
  const response = await page.request.get(`/api/series/${REAL_SERIES_ID}`);
  if (!response.ok()) return null;
  const body = await response.json();
  const season = body.seasons?.[0];
  if (!season?.episodes?.length) return null;
  return { episodeId: season.episodes[0].id, episodeCount: body.total_episodes };
}

test("watched state survives a full page reload", async ({ page }) => {
  const catalog = await realSeries(page);
  test.skip(catalog === null, "the public catalogue is unreachable");

  await page.request.put(
    `/api/series/${REAL_SERIES_ID}/episodes/${catalog!.episodeId}/watched`,
    { data: { watched: true } },
  );

  await page.goto(`/series/${REAL_SERIES_ID}`);
  await expect(page.getByTestId("overall-progress")).toContainText("1 of");

  await page.reload();

  await expect(page.getByTestId("overall-progress")).toContainText("1 of");
  await expect(
    page.getByLabel(/Mark S01E01 .* as watched/),
  ).toBeChecked();

  const viewer = (await page.context().cookies()).find(
    (cookie) => cookie.name === "tv_insight_viewer",
  );
  expect(viewer?.httpOnly).toBe(true);
});

test("the insight is generated on demand, and again on every request", async ({
  page,
}) => {
  const catalog = await realSeries(page);
  test.skip(catalog === null, "the public catalogue is unreachable");

  // The provider may be intentionally unreachable (to exercise the fallback), so
  // this asserts *when* the app asks, not what the provider answers.
  const insightRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/insight")) insightRequests.push(request.url());
  });

  await page.goto(`/series/${REAL_SERIES_ID}`);

  const panel = page.getByTestId("insight-panel");
  await expect(panel).toHaveAttribute("aria-busy", "false");
  // Nothing is requested until the user asks.
  await expect(page.getByTestId("insight-text")).toHaveCount(0);
  await expect.poll(() => insightRequests.length).toBe(0);

  await page.getByRole("button", { name: /view insights/i }).click();
  await expect(page.getByTestId("insight-text")).not.toBeEmpty();
  // The loading state is cleared once an answer lands (model or fallback).
  await expect(panel).toHaveAttribute("aria-busy", "false");
  await expect.poll(() => insightRequests.length).toBe(1);
  expect(insightRequests[0]).not.toContain("refresh=true");

  // Asking again generates again (the default has no reuse window), and the
  // current answer stays visible while the new one is on its way.
  await page.getByRole("button", { name: /regenerate/i }).click();
  await expect(panel).toHaveAttribute("aria-busy", "false");
  await expect(page.getByTestId("insight-text")).not.toBeEmpty();
  await expect.poll(() => insightRequests.length).toBe(2);
  expect(insightRequests[1]).toContain("refresh=true");
});

test("the UI explains upstream failures instead of breaking", async ({ page }) => {
  await page.route("**/api/series/search**", (route) =>
    route.fulfill({
      status: 502,
      json: { error: "ExternalServiceError", detail: "TVMaze is unreachable" },
    }),
  );

  await page.goto("/");
  await page.getByLabel(/find a tv series/i).fill("breaking");

  await expect(page.getByRole("alert")).toContainText(/catalogue is not answering/i);
});

test("a new guest session does not inherit watched state", async ({ page }) => {
  const catalog = await realSeries(page);
  test.skip(catalog === null, "the public catalogue is unreachable");

  await page.request.put(
    `/api/series/${REAL_SERIES_ID}/episodes/${catalog!.episodeId}/watched`,
    { data: { watched: true } },
  );

  await page.goto(`/series/${REAL_SERIES_ID}`);
  await expect(page.getByTestId("overall-progress")).toContainText("1 of");

  // Starting a new guest session must not carry the watched state over.
  await page.getByTestId("new-session").click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto(`/series/${REAL_SERIES_ID}`);
  await expect(page.getByTestId("overall-progress")).toContainText("0 of");
});
