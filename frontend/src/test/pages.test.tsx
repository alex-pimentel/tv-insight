import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { InsightPanel } from "../components/InsightPanel";
import { SearchPage } from "../pages/SearchPage";
import { SeriesPage } from "../pages/SeriesPage";
import { stubFetch } from "../test/fetchMock";
import { seriesDetail } from "../test/fixtures";

function renderWithRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

/** Mounts a route driven page with real params, as the router would. */
function renderRoute(path: string, pattern: string, ui: ReactElement) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={pattern} element={ui} />
      </Routes>
    </MemoryRouter>,
  );
}

function renderSeriesPage(path = "/series/1") {
  return renderRoute(path, "/series/:seriesId", <SeriesPage />);
}

const insight = {
  text: "This one leans into moral ambiguity.",
  provider: "rule_based",
  degraded: true,
  cached: false,
  generated_at: "2024-01-01T12:00:00Z",
  target: "series",
  target_id: 1,
  based_on_comment_count: 2,
  notes: ["huggingface: skipped, not configured"],
};

describe("SearchPage", () => {
  it("does not call the API for a one character query", async () => {
    const fetchSpy = stubFetch([]);
    renderWithRouter(<SearchPage />);

    await userEvent.type(screen.getByLabelText(/find a tv series/i), "b");

    expect(fetchSpy.calls).toHaveLength(0);
  });

  it("renders the matching series", async () => {
    stubFetch([
      [
        "/api/series/search",
        { body: { query: "breaking", count: 1, results: [seriesSearchCard()] } },
      ],
    ]);
    renderWithRouter(<SearchPage />);

    await userEvent.type(screen.getByLabelText(/find a tv series/i), "breaking");

    expect(await screen.findByTestId("results")).toBeInTheDocument();
    expect(screen.getByText("Breaking Bad")).toBeInTheDocument();
    expect(screen.getByText(/2008/)).toBeInTheDocument();
  });

  it("reports an empty result set", async () => {
    stubFetch([["/api/series/search", { body: { query: "zzz", count: 0, results: [] } }]]);
    renderWithRouter(<SearchPage />);

    await userEvent.type(screen.getByLabelText(/find a tv series/i), "zzz");

    expect(await screen.findByTestId("no-results")).toHaveTextContent("zzz");
  });

  it("surfaces an API error with a friendly message", async () => {
    stubFetch([
      [
        "/api/series/search",
        { status: 502, body: { error: "ExternalServiceError", detail: "upstream down" } },
      ],
    ]);
    renderWithRouter(<SearchPage />);

    await userEvent.type(screen.getByLabelText(/find a tv series/i), "breaking");

    expect(await screen.findByRole("alert")).toHaveTextContent(/catalogue is not answering/i);
  });
});

describe("InsightPanel", () => {
  it("does not call the model until the user asks for it", async () => {
    const fetchSpy = stubFetch([["/insight", { body: insight }]]);
    renderWithRouter(<InsightPanel seriesId={1} commentCount={0} />);

    // Nothing is requested on mount: generation is an explicit action.
    expect(fetchSpy.calls).toHaveLength(0);
    expect(screen.getByTestId("insight-generate")).toBeInTheDocument();
    expect(screen.queryByTestId("insight-text")).not.toBeInTheDocument();
  });

  it("shows the insight and its provenance after asking for it", async () => {
    stubFetch([["/insight", { body: insight }]]);
    renderWithRouter(<InsightPanel seriesId={1} commentCount={0} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    expect(await screen.findByTestId("insight-text")).toHaveTextContent(
      "This one leans into moral ambiguity.",
    );
    expect(screen.getByTestId("insight-provider")).toHaveTextContent("rule_based");
    expect(screen.getByText(/offline fallback/i)).toBeInTheDocument();
    expect(screen.getByTestId("insight-basis")).toHaveTextContent("based on 2 comments");
  });

  it("falls back to the heuristic when the provider fails", async () => {
    stubFetch([["/insight", { body: { ...insight, degraded: true } }]]);
    renderWithRouter(<InsightPanel seriesId={1} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    expect(await screen.findByText(/offline fallback/i)).toBeInTheDocument();
  });

  describe("loading feedback", () => {
    it("marks the panel busy and shows a labelled skeleton on the first generation", async () => {
      stubFetch([["/insight", { body: insight, delayMs: 40 }]]);
      renderWithRouter(<InsightPanel seriesId={1} commentCount={0} />);

      await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

      // The panel announces that it is working, in a way a screen reader can read.
      const panel = screen.getByTestId("insight-panel");
      expect(panel).toHaveAttribute("aria-busy", "true");
      expect(screen.getByRole("status")).toHaveTextContent(/generating/i);
      expect(screen.getByTestId("insight-skeleton")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /generating/i })).toBeDisabled();

      // ...and it settles when the answer arrives.
      expect(await screen.findByTestId("insight-text")).toBeInTheDocument();
      await waitFor(() => expect(panel).toHaveAttribute("aria-busy", "false"));
      expect(screen.queryByTestId("insight-skeleton")).not.toBeInTheDocument();
    });

    it("keeps the current answer visible while regenerating", async () => {
      stubFetch([["/insight", { body: insight, delayMs: 40 }]]);
      renderWithRouter(<InsightPanel seriesId={1} />);

      await userEvent.click(screen.getByRole("button", { name: /view insights/i }));
      const text = await screen.findByTestId("insight-text");

      await userEvent.click(screen.getByRole("button", { name: /regenerate/i }));

      // The old answer is dimmed, not replaced: the user keeps reading it.
      expect(screen.getByTestId("insight-text")).toBe(text);
      expect(text).toHaveClass("opacity-40");
      expect(screen.getByRole("button", { name: /regenerating/i })).toBeDisabled();
      expect(screen.queryByTestId("insight-skeleton")).not.toBeInTheDocument();

      await waitFor(() => expect(screen.getByTestId("insight-text")).toHaveClass("opacity-100"));
    });

    it("animates the answer in, and only then reveals the provenance", async () => {
      stubFetch([["/insight", { body: insight }]]);
      renderWithRouter(<InsightPanel seriesId={1} />);

      await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

      expect(await screen.findByTestId("insight-text")).toHaveClass("animate-fade-up");
      // The metadata fades in with the answer it describes.
      expect(screen.getByTestId("insight-provider").parentElement).toHaveClass(
        "animate-fade-up",
      );
    });

    it("replays the animation for a second answer", async () => {
      stubFetch([["/insight", { body: insight, delayMs: 10 }]]);
      renderWithRouter(<InsightPanel seriesId={1} />);

      await userEvent.click(screen.getByRole("button", { name: /view insights/i }));
      const first = await screen.findByTestId("insight-text");

      await userEvent.click(screen.getByRole("button", { name: /regenerate/i }));
      await waitFor(() => {
        expect(screen.getByTestId("insight-text")).not.toBe(first);
      });
      expect(screen.getByTestId("insight-text")).toHaveClass("animate-fade-up");
    });

    it("frees the panel when the request fails", async () => {
      stubFetch([
        [
          "/insight",
          { status: 503, body: { error: "ProviderUnavailable", detail: "down" }, delayMs: 20 },
        ],
      ]);
      renderWithRouter(<InsightPanel seriesId={1} />);

      await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

      expect(await screen.findByRole("alert")).toBeInTheDocument();
      await waitFor(() =>
        expect(screen.getByTestId("insight-panel")).toHaveAttribute("aria-busy", "false"),
      );
      // The action is offered again instead of leaving a dead, disabled button.
      expect(screen.getByRole("button", { name: /view insights/i })).toBeEnabled();
    });
  });

  it("flags an insight that was reused from the store", async () => {
    stubFetch([["/insight", { body: { ...insight, cached: true, provider: "huggingface" } }]]);
    renderWithRouter(<InsightPanel seriesId={1} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    expect(await screen.findByTestId("insight-cached")).toHaveTextContent("reused");
  });

  it("tells the user how many comments arrived since the insight", async () => {
    stubFetch([["/insight", { body: insight }]]);
    renderWithRouter(<InsightPanel seriesId={1} commentCount={5} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    expect(await screen.findByTestId("insight-stale")).toHaveTextContent("3 new comments");
  });

  it("does not flag staleness while the insight is up to date", async () => {
    stubFetch([["/insight", { body: insight }]]);
    renderWithRouter(<InsightPanel seriesId={1} commentCount={2} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    await screen.findByTestId("insight-text");
    expect(screen.queryByTestId("insight-stale")).not.toBeInTheDocument();
  });

  it("forces a regeneration on request", async () => {
    const fetchSpy = stubFetch([["/insight", { body: insight }]]);
    renderWithRouter(<InsightPanel seriesId={1} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));
    await screen.findByTestId("insight-text");
    await userEvent.click(screen.getByRole("button", { name: /regenerate/i }));

    expect(fetchSpy.calls.some((call) => call.url.includes("refresh=true"))).toBe(true);
  });

  it("returns to the idle state when the subject changes", async () => {
    stubFetch([["/insight", { body: insight }]]);
    const { rerender } = render(
      <MemoryRouter>
        <InsightPanel key="series-1" seriesId={1} />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));
    await screen.findByTestId("insight-text");

    rerender(
      <MemoryRouter>
        <InsightPanel key="series-2" seriesId={2} />
      </MemoryRouter>,
    );

    expect(screen.queryByTestId("insight-text")).not.toBeInTheDocument();
    expect(screen.getByTestId("insight-generate")).toBeInTheDocument();
  });

  it("degrades gracefully when the provider fails", async () => {
    stubFetch([
      ["/insight", { status: 503, body: { error: "ProviderUnavailable", detail: "all down" } }],
    ]);
    renderWithRouter(<InsightPanel seriesId={1} />);

    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/insight service is unavailable/i);
  });
});

describe("SeriesPage", () => {
  function routes(detail = seriesDetail()) {
    return [
      ["/comments", { body: detail.comments }],
      ["/insight", { body: insight }],
      [`/api/series/${detail.series.id}`, { body: detail }],
      [
        "/watched",
        (_url: string, init?: RequestInit) => ({
          body: { watched: init?.body ? JSON.parse(String(init.body)).watched : false },
        }),
      ],
    ] as [string, { status?: number; body?: unknown }][];
  }

  it("renders the series, its seasons and the overall progress", async () => {
    stubFetch(routes());
    renderSeriesPage();

    expect(await screen.findByTestId("series-title")).toHaveTextContent("Breaking Bad");
    expect(screen.getByTestId("overall-progress")).toHaveTextContent(
      "0 of 4 episodes watched",
    );
    expect(screen.getAllByTestId("episode-row")).toHaveLength(2);
  });

  it("uses the original poster, 50% larger, in the detail header", async () => {
    stubFetch(routes());
    renderSeriesPage();

    const poster = await screen.findByTestId("series-poster");
    // The header shows the original (not the search grid's thumbnail)...
    expect(poster).toHaveAttribute("src", "https://example.test/bb.jpg");
    // ...at 1.5x the previous size (h-64/w-44 -> h-96/w-66).
    expect(poster).toHaveClass("h-96", "w-66");
  });

  it("persists a watched toggle to the API and updates progress", async () => {
    const fetchSpy = stubFetch(routes());
    renderSeriesPage();

    await screen.findByTestId("series-title");
    await userEvent.click(screen.getByLabelText("Mark S01E01 Episode 1 as watched"));

    const put = fetchSpy.calls.find((call) => call.method === "PUT");
    expect(put?.url).toContain("/api/series/1/episodes/101/watched");
    expect(put?.body).toEqual({ watched: true });
    expect(screen.getByTestId("overall-progress")).toHaveTextContent(
      "1 of 4 episodes watched",
    );
  });

  it("rolls back the optimistic toggle when the write fails", async () => {
    stubFetch([
      ["/comments", { body: [] }],
      ["/insight", { body: insight }],
      ["/watched", { status: 500, body: { error: "ExternalServiceError" } }],
      ["/api/series/1", { body: seriesDetail() }],
    ]);
    renderSeriesPage();

    await screen.findByTestId("series-title");
    const checkbox = screen.getByLabelText("Mark S01E01 Episode 1 as watched");
    await userEvent.click(checkbox);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByTestId("overall-progress")).toHaveTextContent(
      "0 of 4 episodes watched",
    );
  });

  it("posts a new comment and shows it at once", async () => {
    const created = {
      id: "c9",
      target: "series" as const,
      series_id: 1,
      episode_id: null,
      episode_code: null,
      text: "New thought",
      created_at: "2024-02-01T00:00:00Z",
      author: "Anonymous viewer",
      mine: true,
    };
    // After the POST the GET returns the comment too (read-your-writes).
    let posted = false;
    stubFetch([
      [
        "/comments",
        (_url: string, init?: RequestInit) => {
          if (init?.method === "POST") {
            posted = true;
            return { status: 201, body: created };
          }
          return { body: posted ? [created] : [] };
        },
      ],
      ["/insight", { body: insight }],
      ["/api/series/1", { body: seriesDetail() }],
    ]);
    renderSeriesPage();

    await screen.findByTestId("series-title");
    await userEvent.type(screen.getByLabelText(/your comment/i), "New thought");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(await screen.findByText("New thought")).toBeInTheDocument();
  });

  it("refreshes the comment list from the server after posting", async () => {
    const created = {
      id: "c9",
      target: "series" as const,
      series_id: 1,
      episode_id: null,
      episode_code: null,
      text: "My thought",
      created_at: "2024-02-01T00:00:00Z",
      author: "Anonymous viewer",
      mine: true,
    };
    const others = {
      id: "c10",
      target: "series" as const,
      series_id: 1,
      episode_id: null,
      episode_code: null,
      text: "Someone else's thought",
      created_at: "2024-02-01T00:00:05Z",
      author: "Anonymous viewer",
      mine: false,
    };
    let posted = false;
    stubFetch([
      [
        "/comments",
        (_url: string, init?: RequestInit) => {
          if (init?.method === "POST") {
            posted = true;
            return { status: 201, body: created };
          }
          // The refresh sees the new comment *and* one posted meanwhile.
          return { body: posted ? [created, others] : [] };
        },
      ],
      ["/insight", { body: insight }],
      ["/api/series/1", { body: seriesDetail() }],
    ]);
    renderSeriesPage();

    await screen.findByTestId("series-title");
    await userEvent.type(screen.getByLabelText(/your comment/i), "My thought");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(await screen.findByText("My thought")).toBeInTheDocument();
    expect(await screen.findByText("Someone else's thought")).toBeInTheDocument();
  });

  it("shows a not found message for an unknown series", async () => {
    stubFetch([
      ["/comments", { body: [] }],
      ["/api/series/1", { status: 404, body: { error: "ResourceNotFound" } }],
    ]);
    renderSeriesPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /could not find that title/i,
    );
  });
});

function seriesSearchCard() {
  return {
    id: 1,
    name: "Breaking Bad",
    year: 2008,
    poster_url: null,
    poster_thumbnail_url: null,
    genres: ["Drama"],
    status: "Ended",
    rating: 9.2,
    network: "AMC",
    language: "English",
  };
}

describe("stubFetch", () => {
  it("fails loudly when a call is not stubbed", async () => {
    stubFetch([]);
    const response = await fetch("/api/unknown");
    expect(response.status).toBe(404);
  });
});
