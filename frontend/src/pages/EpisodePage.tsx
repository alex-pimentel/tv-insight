import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Comment, EpisodeDetail } from "../api/types";
import { CommentForm } from "../components/CommentForm";
import { CommentList } from "../components/CommentList";
import { ErrorNotice } from "../components/ErrorNotice";
import { InsightPanel } from "../components/InsightPanel";
import { Spinner } from "../components/Spinner";

export function EpisodePage() {
  const { seriesId, episodeId } = useParams();
  const series = Number(seriesId);
  const episode = Number(episodeId);

  const [detail, setDetail] = useState<EpisodeDetail | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [episodeDetail, episodeComments] = await Promise.all([
        api.episodeDetail(series, episode),
        api.listComments(series, episode),
      ]);
      setDetail(episodeDetail);
      setComments(episodeComments);
    } catch (caught) {
      setError(caught);
    } finally {
      setLoading(false);
    }
  }, [series, episode]);

  useEffect(() => {
    void load();
  }, [load]);

  // Re-reads the comments so the list matches the server (authoritative order,
  // and anything other viewers added meanwhile) without reloading the page.
  // Best effort: the optimistic list is already shown, so a failed refresh is
  // not worth an error banner.
  const refreshComments = useCallback(async () => {
    try {
      setComments(await api.listComments(series, episode));
    } catch {
      // Intentionally swallowed - see above.
    }
  }, [series, episode]);

  async function handleAddComment(text: string) {
    const created = await api.addComment(series, text, episode);
    setComments((current) => [created, ...current]);
    await refreshComments();
  }

  async function handleToggleWatched(watched: boolean) {
    if (!detail) return;
    setDetail({ ...detail, episode: { ...detail.episode, watched } });
    try {
      await api.setWatched(series, episode, watched);
    } catch (caught) {
      await load();
      setError(caught);
    }
  }

  if (loading && !detail) return <Spinner label="Loading episode…" />;
  if (error && !detail) return <ErrorNotice error={error} onRetry={() => void load()} />;
  if (!detail) return null;

  return (
    <div className="space-y-8">
      {error ? <ErrorNotice error={error} onRetry={() => void load()} /> : null}

      <nav className="text-sm text-muted">
        <Link to={`/series/${series}`} className="hover:text-accent-soft">
          ← {detail.series.name}
        </Link>
      </nav>

      <header className="space-y-3">
        <p className="font-mono text-sm text-muted" data-testid="episode-code">
          {detail.episode.code}
        </p>
        <h1 className="text-3xl font-bold" data-testid="episode-title">
          {detail.episode.name}
        </h1>
        <p className="text-sm text-muted">
          {detail.episode.airdate ?? "air date unknown"}
          {detail.episode.runtime_minutes
            ? ` · ${detail.episode.runtime_minutes} min`
            : ""}
        </p>
        <label className="inline-flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={detail.episode.watched}
            onChange={(event) => void handleToggleWatched(event.target.checked)}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Watched
        </label>
        <p className="max-w-3xl text-sm leading-relaxed text-ink">
          {detail.episode.summary}
        </p>
      </header>

      <InsightPanel
        key={`episode-${episode}`}
        seriesId={series}
        episodeId={episode}
        commentCount={comments.length}
      />

      <section aria-labelledby="comments-heading" className="space-y-3">
        <h2 id="comments-heading" className="text-xl font-semibold">
          Comments <span className="text-sm font-normal text-muted">({comments.length})</span>
        </h2>
        <CommentForm onSubmit={handleAddComment} placeholder="What did you think of this episode?" />
        <CommentList comments={comments} emptyMessage="No comments on this episode yet." />
      </section>

      {detail.next_episode ? (
        <footer className="border-t border-line pt-4">
          <Link
            to={`/series/${series}/episodes/${detail.next_episode.id}`}
            className="text-sm text-accent-soft hover:underline"
          >
            Next: {detail.next_episode.code} — {detail.next_episode.name} →
          </Link>
        </footer>
      ) : null}
    </div>
  );
}
