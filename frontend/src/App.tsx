import { useEffect, useState } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { api } from "./api/client";
import type { Health } from "./api/types";
import { ThemeToggle } from "./components/ThemeToggle";
import { EpisodePage } from "./pages/EpisodePage";
import { SearchPage } from "./pages/SearchPage";
import { SeriesPage } from "./pages/SeriesPage";

function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  if (!health) return null;

  const available = health.insights.filter((provider) => provider.available);
  const names = available.map((provider) => provider.provider);
  // Every configured tier is listed with its state and model, including the ones
  // that are off: a provider with a token but a stale model id is the most common
  // way for a "configured" provider to start failing, and this makes it visible
  // without reading logs.
  const detail = health.insights
    .map((provider) => {
      const state = provider.available ? "on" : "off";
      const label = provider.model
        ? `${provider.provider} (${provider.model})`
        : provider.provider;
      return `${label} ${state}`;
    })
    .join(" · ");

  return (
    <span
      data-testid="health-badge"
      title={`database: ${health.database} · ai: ${detail || "none"}`}
      className="hidden rounded-full bg-overlay px-2.5 py-1 text-[11px] text-muted sm:inline"
    >
      db {health.database} · ai {names.length > 0 ? names.join("/") : "offline"}
    </span>
  );
}

/**
 * Starts a fresh guest session.
 *
 * There is no registration by design (see the client feedback): a visitor browses
 * as a guest carried by an httpOnly cookie. This button makes that explicit and,
 * in a demo, proves that watched state and comments are scoped to the session.
 */
function GuestSessionButton() {
  const [busy, setBusy] = useState(false);

  async function startFreshSession() {
    setBusy(true);
    try {
      await api.resetSession();
    } finally {
      window.location.assign("/");
    }
  }

  return (
    <button
      type="button"
      data-testid="new-session"
      onClick={() => void startFreshSession()}
      disabled={busy}
      title="Start a new guest session (clears watched state and comments for this browser)"
      className="rounded-full bg-overlay px-2.5 py-1 text-[11px] text-muted hover:bg-card-hover disabled:opacity-50"
    >
      {busy ? "…" : "guest session · new"}
    </button>
  );
}

export function App() {
  return (
    <div className="min-h-full">
      <header className="border-b border-line bg-card/60 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold">
            <span aria-hidden="true">📺</span> tv-insight
          </Link>
          <div className="flex items-center gap-2">
            <HealthBadge />
            <ThemeToggle />
            <GuestSessionButton />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <Routes>
          <Route path="/" element={<SearchPage />} />
          <Route path="/series/:seriesId" element={<SeriesPage />} />
          <Route path="/series/:seriesId/episodes/:episodeId" element={<EpisodePage />} />
          <Route
            path="*"
            element={<p className="text-muted">That page does not exist.</p>}
          />
        </Routes>
      </main>

      <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-muted">
        Data from the public TVMaze API · insights generated on demand with a fallback
        chain.
      </footer>
    </div>
  );
}
