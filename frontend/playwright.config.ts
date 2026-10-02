import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:7777";

/**
 * End to end configuration.
 *
 * The suite runs against the containerised application (`docker compose up`), so
 * it exercises the real image: FastAPI, the built React bundle, the cookie based
 * viewer identity and PostgreSQL.
 *
 * `make test-e2e` runs it from a container that shares the application's network
 * namespace and points at `http://localhost:7777`. That matters: recent Chromium
 * builds upgrade plain HTTP navigations for non-loopback hosts ("HTTPS-First
 * Mode"), which surfaces as ERR_SSL_PROTOCOL_ERROR against a container hostname.
 * Loopback is exempt, so the test keeps exercising the same process on the same
 * port without fighting the browser.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",

  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],

  expect: { timeout: 10_000 },
});
