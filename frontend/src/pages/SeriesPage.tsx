import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Comment, Episode, SeriesDetail } from "../api/types";
import { CommentForm } from "../components/CommentForm";
import { CommentList } from "../components/CommentList";
import { ErrorNotice } from "../components/ErrorNotice";
import { InsightPanel } from "../components/InsightPanel";
import { ProgressBar } from "../components/ProgressBar";
import { SeasonAccordion } from "../components/SeasonAccordion";
import { Spinner } from "../components/Spinner";
import { overallProgress, withEpisodeWatched } from "../lib/progress";

export function SeriesPage() {
  const { seriesId } = useParams();
  const id = Number(seriesId);

  const [detail, setDetail] = useState<SeriesDetail | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [series, seriesComments] = await Promise.all([
        api.seriesDetail(id),
        api.listComments(id),
      ]);
      setDetail(series);
      setComments(seriesComments);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  // Re-reads only the comments, so a new one can be reconciled with the server
  // (authoritative order, and comments other viewers added meanwhile) without a
  // full page reload. Best effort: a failed reconciliation must not turn a
  // successful post into an error, and the optimistic list is already on screen.
  const refreshComments = useCallback(async () => {
    try {
      setComments(await api.listComments(id));
    } catch {
      // Intentionally swallowed - see above.
    }
  }, [id]);

  async function handleToggleWatched(episode: Episode, watched: boolean) {
    // Optimistic: the checkbox flips immediately, and reverts if the write fails.
    setDetail((current) =>
      current
        ? { ...current, seasons: withEpisodeWatched(current.seasons, episode.id, watched) }
        : current,
    );
    try {
      await api.setWatched(id, episode.id, watched);
    } catch (caught) {
      // Reload first (which clears any previous error), then surface this one so
      // the banner stays visible with the reverted state underneath it.
      await load();
      setError(caught);
    }
  }

  async function handleAddComment(text: string) {
    const created = await api.addComment(id, text);
    // Show it at once, then refresh the list so it matches the server.
    setComments((current) => [created, ...current]);
    setDetail((current) =>
      current ? { ...current, comment_count: current.comment_count + 1 } : current,
    );
    await refreshComments();
  }

  if (loading && !detail) return <Spinner label="Loading series…" />;
  if (error && !detail) return <ErrorNotice error={error} onRetry={() => void load()} />;
  if (!detail) return null;

  const overall = overallProgress(detail.seasons);

  return (
    <div className="space-y-8">
      {/* A failed write must not blank the page: show a banner and keep the data. */}
      {error ? <ErrorNotice error={error} onRetry={() => void load()} /> : null}

      <nav className="text-sm text-muted">
        <Link to="/" className="hover:text-accent-soft">
          ← Back to search
        </Link>
      </nav>

      <header className="flex flex-col gap-6 sm:flex-row">
        {detail.series.poster_url ? (
          // Detail header shows the *original* image, 50% larger than before
          // (h-64/w-44 = 16rem x 11rem -> h-96/w-66 = 24rem x 16.5rem).
          <img
            src={detail.series.poster_url}
            alt={`${detail.series.name} poster`}
            data-testid="series-poster"
            className="h-96 w-66 shrink-0 rounded-xl object-cover"
          />
        ) : null}

        <div className="flex-1 space-y-3">
          <div>
            <h1 className="text-3xl font-bold" data-testid="series-title">
              {detail.series.name}
            </h1>
            <p className="mt-1 text-sm text-muted">
              {detail.series.year ?? "—"}
              {detail.series.network ? ` · ${detail.series.network}` : ""}
              {detail.series.status ? ` · ${detail.series.status}` : ""}
              {detail.series.rating !== null ? ` · ★ ${detail.series.rating}` : ""}
            </p>
          </div>

          {detail.series.genres.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {detail.series.genres.map((genre) => (
                <li
                  key={genre}
                  className="rounded-full bg-overlay px-2.5 py-1 text-xs text-ink"
                >
                  {genre}
                </li>
              ))}
            </ul>
          ) : null}

          <p className="max-w-3xl text-sm leading-relaxed text-ink">
            {detail.summary}
          </p>

          <div className="max-w-md">
            <ProgressBar
              value={overall.progress}
              label="Overall progress"
              className="mt-2"
            />
            <p className="mt-1 text-xs text-muted" data-testid="overall-progress">
              {overall.watched} of {overall.total} episodes watched
            </p>
          </div>
        </div>
      </header>

      <InsightPanel
        key={`series-${id}`}
        seriesId={id}
        commentCount={detail.comment_count}
      />

      <section aria-labelledby="episodes-heading" className="space-y-3">
        <h2 id="episodes-heading" className="text-xl font-semibold">
          Episodes
        </h2>
        <SeasonAccordion
          seriesId={id}
          seasons={detail.seasons}
          onToggleWatched={(episode, watched) => void handleToggleWatched(episode, watched)}
        />
      </section>

      <section aria-labelledby="comments-heading" className="space-y-3">
        <h2 id="comments-heading" className="text-xl font-semibold">
          Comments{" "}
          <span className="text-sm font-normal text-muted">
            ({detail.comment_count})
          </span>
        </h2>
        <CommentForm
          onSubmit={handleAddComment}
          placeholder="What do you think about this series?"
        />
        <CommentList comments={comments} emptyMessage="Be the first to comment." />
      </section>
    </div>
  );
}
