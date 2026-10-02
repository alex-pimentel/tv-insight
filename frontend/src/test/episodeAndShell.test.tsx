import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { EpisodePage } from "../pages/EpisodePage";
import { stubFetch } from "./fetchMock";

const HEALTH = {
  status: "ok",
  version: "1.0.0",
  database: "up",
  insights: [
    { provider: "huggingface", available: false, model: "meta-llama/Llama-3.1-8B-Instruct" },
    { provider: "heuristic", available: true, model: null },
  ],
};

const SERIES = {
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

function episode(watched = false) {
  return {
    id: 101,
    name: "Pilot",
    season: 1,
    number: 1,
    code: "S01E01",
    summary: "Where it all starts.",
    airdate: "2008-01-20",
    runtime_minutes: 47,
    image_url: null,
    watched,
  };
}

const EPISODE_DETAIL = {
  series: SERIES,
  episode: episode(),
  comment_count: 1,
  comments: [
    {
      id: "c1",
      target: "episode",
      series_id: 1,
      episode_id: 101,
      episode_code: "S01E01",
      text: "What a start",
      created_at: "2024-01-01T12:00:00Z",
      author: "Anonymous viewer",
      mine: true,
    },
  ],
  next_episode: { ...episode(), id: 102, number: 2, code: "S01E02", name: "Second" },
};

const INSIGHT = {
  text: "A grounded crime drama.",
  provider: "heuristic",
  degraded: true,
  cached: false,
  generated_at: "2024-01-01T12:00:00Z",
  target: "episode",
  target_id: 101,
  based_on_comment_count: 1,
  notes: [],
};

function episodeRoutes(overrides: Record<string, unknown> = {}) {
  // Overrides come first: handlers are matched in order, so they win.
  return [
    ...Object.entries(overrides).map(
      ([pattern, response]) => [pattern, response] as [string, { body?: unknown }],
    ),
    ["/api/health", { body: HEALTH }],
    ["/insight", { body: INSIGHT }],
    ["/comments", { body: EPISODE_DETAIL.comments }],
    ["/watched", { body: { watched: true } }],
    ["/api/series/1/episodes/101", { body: EPISODE_DETAIL }],
  ] as [string, { status?: number; body?: unknown }][];
}

function renderEpisodePage() {
  return render(
    <MemoryRouter initialEntries={["/series/1/episodes/101"]}>
      <Routes>
        <Route path="/series/:seriesId/episodes/:episodeId" element={<EpisodePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("EpisodePage", () => {
  it("renders the episode header, comments and the AI insight on demand", async () => {
    stubFetch(episodeRoutes());
    renderEpisodePage();

    expect(await screen.findByTestId("episode-code")).toHaveTextContent("S01E01");
    expect(screen.getByTestId("episode-title")).toHaveTextContent("Pilot");
    expect(screen.getByText("What a start")).toBeInTheDocument();
    expect(screen.getByText(/47 min/)).toBeInTheDocument();

    // The insight is not fetched until asked for.
    await userEvent.click(screen.getByRole("button", { name: /view insights/i }));
    expect(await screen.findByTestId("insight-text")).toHaveTextContent(
      "A grounded crime drama.",
    );
  });

  it("links to the next episode", async () => {
    stubFetch(episodeRoutes());
    renderEpisodePage();

    const next = await screen.findByRole("link", { name: /next: S01E02/i });
    expect(next).toHaveAttribute("href", "/series/1/episodes/102");
  });

  it("toggles watched through the API", async () => {
    const spy = stubFetch(episodeRoutes());
    renderEpisodePage();

    await screen.findByTestId("episode-title");
    await userEvent.click(screen.getByRole("checkbox", { name: /watched/i }));

    await waitFor(() => {
      expect(spy.calls.some((call) => call.method === "PUT")).toBe(true);
    });
  });

  it("reverts the toggle and warns when the write fails", async () => {
    stubFetch(episodeRoutes({ "/watched": { status: 500, body: { error: "ExternalServiceError" } } }));
    renderEpisodePage();

    await screen.findByTestId("episode-title");
    const checkbox = screen.getByRole("checkbox", { name: /watched/i });
    await userEvent.click(checkbox);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await waitFor(() => expect(checkbox).not.toBeChecked());
  });

  it("posts a comment on the episode", async () => {
    const created = {
      id: "c9",
      target: "episode" as const,
      series_id: 1,
      episode_id: 101,
      episode_code: "S01E01",
      text: "New episode note",
      created_at: "2024-02-01T00:00:00Z",
      author: "Anonymous viewer",
      mine: true,
    };
    // The GET and the POST share a path, so the handler answers by method. The
    // GET returns the comment once it has been posted, to mirror read-your-writes.
    let posted = false;
    stubFetch([
      ["/api/health", { body: HEALTH }],
      ["/insight", { body: INSIGHT }],
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
      ["/api/series/1/episodes/101", { body: { ...EPISODE_DETAIL, comments: [] } }],
    ]);
    renderEpisodePage();

    await screen.findByTestId("episode-title");
    await userEvent.type(screen.getByLabelText(/your comment/i), "New episode note");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(await screen.findByText("New episode note")).toBeInTheDocument();
  });

  it("refreshes the episode comment list after posting", async () => {
    const created = {
      id: "c9",
      target: "episode" as const,
      series_id: 1,
      episode_id: 101,
      episode_code: "S01E01",
      text: "My episode note",
      created_at: "2024-02-01T00:00:00Z",
      author: "Anonymous viewer",
      mine: true,
    };
    const others = {
      id: "c10",
      target: "episode" as const,
      series_id: 1,
      episode_id: 101,
      episode_code: "S01E01",
      text: "Someone else's episode note",
      created_at: "2024-02-01T00:00:05Z",
      author: "Anonymous viewer",
      mine: false,
    };
    let posted = false;
    stubFetch([
      ["/api/health", { body: HEALTH }],
      ["/insight", { body: INSIGHT }],
      [
        "/comments",
        (_url: string, init?: RequestInit) => {
          if (init?.method === "POST") {
            posted = true;
            return { status: 201, body: created };
          }
          return { body: posted ? [created, others] : [] };
        },
      ],
      ["/api/series/1/episodes/101", { body: { ...EPISODE_DETAIL, comments: [] } }],
    ]);
    renderEpisodePage();

    await screen.findByTestId("episode-title");
    await userEvent.type(screen.getByLabelText(/your comment/i), "My episode note");
    await userEvent.click(screen.getByRole("button", { name: /post comment/i }));

    expect(await screen.findByText("My episode note")).toBeInTheDocument();
    expect(await screen.findByText("Someone else's episode note")).toBeInTheDocument();
  });

  it("shows a not found message when the episode does not exist", async () => {
    stubFetch([
      ["/api/health", { body: HEALTH }],
      ["/comments", { body: [] }],
      ["/api/series/1/episodes/101", { status: 404, body: { error: "ResourceNotFound" } }],
    ]);
    renderEpisodePage();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /could not find that title/i,
    );
  });
});

describe("App shell", () => {
  function renderApp() {
    return render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
  }

  it("renders the header, the search page and the footer", async () => {
    stubFetch([["/api/health", { body: HEALTH }]]);
    renderApp();

    expect(screen.getByRole("link", { name: /tv-insight/i })).toHaveAttribute("href", "/");
    expect(screen.getByLabelText(/find a tv series/i)).toBeInTheDocument();
    expect(screen.getByText(/data from the public tvmaze api/i)).toBeInTheDocument();
    // Await the health request so the state update is settled before the test ends.
    await screen.findByTestId("health-badge");
  });

  it("summarises database and AI availability in the header badge", async () => {
    stubFetch([["/api/health", { body: HEALTH }]]);
    renderApp();

    const badge = await screen.findByTestId("health-badge");
    expect(badge).toHaveTextContent("db up");
    expect(badge).toHaveTextContent("ai heuristic");
    // The configured model travels with the badge, so a stale id is visible.
    expect(badge).toHaveAttribute(
      "title",
      expect.stringContaining("meta-llama/Llama-3.1-8B-Instruct"),
    );
  });

  it("renders the header without the badge when health is unreachable", async () => {
    stubFetch([["/api/health", { status: 500, body: { error: "Boom" } }]]);
    renderApp();

    await waitFor(() =>
      expect(screen.queryByTestId("health-badge")).not.toBeInTheDocument(),
    );
  });

  it("shows a fallback message for an unknown client route", async () => {
    stubFetch([["/api/health", { body: HEALTH }]]);
    render(
      <MemoryRouter initialEntries={["/nowhere"]}>
        <App />
      </MemoryRouter>,
    );

    expect(await screen.findByText(/that page does not exist/i)).toBeInTheDocument();
  });

  it("starts a new guest session on request", async () => {
    const fetchSpy = stubFetch([
      ["/api/health", { body: HEALTH }],
      ["/api/session/reset", { status: 204 }],
    ]);
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, assign },
    });

    renderApp();
    await userEvent.click(screen.getByTestId("new-session"));

    await waitFor(() =>
      expect(
        fetchSpy.calls.some((call) => call.url.includes("/api/session/reset")),
      ).toBe(true),
    );
    await waitFor(() => expect(assign).toHaveBeenCalledWith("/"));
  });

  it("labels the session as a guest", async () => {
    stubFetch([["/api/health", { body: HEALTH }]]);
    renderApp();

    expect(screen.getByTestId("new-session")).toHaveTextContent(/guest session/i);
  });
});
