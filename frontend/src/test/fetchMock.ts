import { vi } from "vitest";

export interface StubResponse {
  status?: number;
  body?: unknown;
  /**
   * Hold the response for this long. Lets a test observe the loading state that
   * the UI shows while a request is in flight.
   */
  delayMs?: number;
}

export type StubHandler = (
  url: string,
  init?: RequestInit,
) => StubResponse | undefined;

/** Records every call so tests can assert on the exact request that was made. */
export interface FetchSpy {
  calls: { url: string; method: string; body: unknown }[];
}

/**
 * Stubs `fetch` with a list of handlers, matched in order by substring.
 *
 * A hand rolled stub instead of a mocking framework: the frontend only talks to
 * one origin through one helper, so a regex-free matcher is enough and keeps the
 * component tests readable.
 */
export function stubFetch(
  routes: [string, StubResponse | StubHandler][],
): FetchSpy {
  const spy: FetchSpy = { calls: [] };

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      const method = (init?.method ?? "GET").toUpperCase();
      spy.calls.push({
        url,
        method,
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
      });

      for (const [pattern, route] of routes) {
        if (!url.includes(pattern)) continue;
        const resolved = typeof route === "function" ? route(url, init) : route;
        if (!resolved) continue;
        if (resolved.delayMs) {
          await new Promise((resolve) => setTimeout(resolve, resolved.delayMs));
        }
        const status = resolved.status ?? 200;
        // A 204/304 response must not carry a body, or the Response constructor throws.
        const bodyless = status === 204 || status === 205 || status === 304;
        return new Response(bodyless ? null : JSON.stringify(resolved.body ?? null), {
          status,
          headers: { "Content-Type": "application/json" },
        });
      }

      return new Response(
        JSON.stringify({ error: "NotFound", detail: `no stub for ${url}` }),
        { status: 404, headers: { "Content-Type": "application/json" } },
      );
    }),
  );

  return spy;
}
