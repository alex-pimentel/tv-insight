import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { SeriesCard as SeriesCardModel } from "../api/types";
import { ErrorNotice } from "../components/ErrorNotice";
import { SeriesCard } from "../components/SeriesCard";
import { Spinner } from "../components/Spinner";
import { useDebounce } from "../hooks/useDebounce";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SeriesCardModel[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const debouncedQuery = useDebounce(query.trim());

  useEffect(() => {
    // Fewer than two characters is not a search; the API would reject it.
    if (debouncedQuery.length < 2) {
      setResults(null);
      setError(null);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .search(debouncedQuery, controller.signal)
      .then((response) => setResults(response.results))
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") return;
        setError(caught);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [debouncedQuery]);

  return (
    <div className="space-y-6">
      <form
        role="search"
        onSubmit={(event) => event.preventDefault()}
        className="space-y-2"
      >
        <label htmlFor="search" className="block text-sm font-medium text-ink">
          Find a TV series
        </label>
        <input
          id="search"
          type="search"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try “breaking bad”, “dark”, “the wire”…"
          className="w-full rounded-xl border border-line bg-card px-4 py-3 text-base placeholder:text-muted focus:border-accent focus:outline-none"
        />
      </form>

      {loading ? <Spinner label="Searching the catalogue…" /> : null}
      {error ? <ErrorNotice error={error} /> : null}

      {results && results.length === 0 ? (
        <p className="text-muted" data-testid="no-results">
          Nothing found for “{debouncedQuery}”.
        </p>
      ) : null}

      {results && results.length > 0 ? (
        <ul
          data-testid="results"
          className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5"
        >
          {results.map((series) => (
            <li key={series.id}>
              <SeriesCard series={series} />
            </li>
          ))}
        </ul>
      ) : null}

      {results === null && !loading && !error ? (
        <p className="text-muted">
          Search for a series to see its episodes, track what you watched and get an AI
          insight.
        </p>
      ) : null}
    </div>
  );
}
