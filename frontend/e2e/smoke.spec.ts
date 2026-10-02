import { expect, test } from "@playwright/test";

/**
 * Smoke tests against the real running stack.
 *
 * These assert what the deployment itself is responsible for - the process is up,
 * the database answers, the bundle is served and the SPA routes resolve - and
 * deliberately avoid the TVMaze API so they are deterministic in a Jenkins VM.
 */
test.describe("deployment", () => {
  test("health endpoint reports the database as up", async ({ request }) => {
    const response = await request.get("/api/health");

    expect(response.ok()).toBe(true);
    const body = await response.json();
    expect(body.status).toBe("ok");
    expect(body.database).toBe("up");
    expect(Array.isArray(body.insights)).toBe(true);
  });

  test("the built single page application is served at the root", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByLabel(/find a tv series/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /tv-insight/i })).toBeVisible();
  });

  test("unknown client routes still render the SPA (history fallback)", async ({ page }) => {
    await page.goto("/series/424242");

    await expect(page.locator("#root")).not.toBeEmpty();
  });

  test("unknown api routes answer with JSON, not the SPA", async ({ request }) => {
    const response = await request.get("/api/does-not-exist");

    expect(response.status()).toBe(404);
    expect(await response.json()).toMatchObject({ error: "NotFound" });
  });

  test("a viewer cookie is issued and survives reloads", async ({ page }) => {
    await page.goto("/");

    // The identity cookie is minted by the first endpoint that needs a viewer.
    // Listing comments does not touch TVMaze, so this stays offline-safe.
    const response = await page.request.get("/api/series/1/comments");
    expect(response.ok()).toBe(true);

    const viewer = (await page.context().cookies()).find(
      (cookie) => cookie.name === "tv_insight_viewer",
    );
    expect(viewer).toBeDefined();
    expect(viewer?.httpOnly).toBe(true);

    await page.reload();

    const after = (await page.context().cookies()).find(
      (cookie) => cookie.name === "tv_insight_viewer",
    );
    expect(after?.value).toBe(viewer?.value);
  });
});
