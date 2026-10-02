import { describe, expect, it } from "vitest";
import { ApiError, api } from "../api/client";
import { stubFetch } from "../test/fetchMock";

describe("api client", () => {
  it("sends the viewer cookie with every request", async () => {
    stubFetch([["/api/health", { body: { status: "ok" } }]]);
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;

    await api.health();

    expect(fetchMock.mock.calls[0][1]).toMatchObject({ credentials: "same-origin" });
  });

  it("encodes the search query", async () => {
    const spy = stubFetch([["/api/series/search", { body: { query: "a b", count: 0, results: [] } }]]);

    await api.search("a b & c");

    expect(spy.calls[0].url).toContain("q=a%20b%20%26%20c");
  });

  it("turns an error payload into a typed ApiError", async () => {
    stubFetch([
      [
        "/api/series/1",
        { status: 404, body: { error: "ResourceNotFound", detail: "Unknown series 1" } },
      ],
    ]);

    await expect(api.seriesDetail(1)).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      code: "ResourceNotFound",
      message: "Unknown series 1",
    });
  });

  it("handles a non JSON error body", async () => {
    const fetchMock = stubFetch([]);
    void fetchMock;
    globalThis.fetch = (async () =>
      new Response("<html>500</html>", { status: 500 })) as typeof fetch;

    const error = await api.health().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("RequestFailed");
  });

  it("sends the watched flag in the body", async () => {
    const spy = stubFetch([["/watched", { body: { watched: true } }]]);

    await api.setWatched(1, 101, true);

    expect(spy.calls[0]).toMatchObject({
      method: "PUT",
      body: { watched: true },
    });
  });

  it("adds the episode id when commenting on an episode", async () => {
    const spy = stubFetch([["/comments", { status: 201, body: {} }]]);

    await api.addComment(1, "hello", 201);

    expect(spy.calls[0].body).toEqual({ text: "hello", episode_id: 201 });
  });

  it("omits the episode id for series comments", async () => {
    const spy = stubFetch([["/comments", { status: 201, body: {} }]]);

    await api.addComment(1, "hello");

    expect(spy.calls[0].body).toEqual({ text: "hello", episode_id: null });
  });

  it("requests a refresh through the query string", async () => {
    const spy = stubFetch([["/insight", { body: {} }]]);

    await api.seriesInsight(3, true);

    expect(spy.calls[0].url).toBe("/api/series/3/insight?refresh=true");
  });
});
