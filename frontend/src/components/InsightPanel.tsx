import { useCallback, useState } from "react";
import { api } from "../api/client";
import type { Insight } from "../api/types";
import { ErrorNotice } from "./ErrorNotice";
import { Skeleton } from "./Skeleton";
import { Spinner } from "./Spinner";

interface InsightPanelProps {
  seriesId: number;
  episodeId?: number;
  /** How many comments exist right now, shown so the staleness rule is visible. */
  commentCount?: number;
}

/**
 * The AI feature.
 *
 * Generation is **explicit**: nothing is requested until the user asks for it with
 * the "View insights" button - the behaviour the client chose over firing a model
 * call on every details page. Once generated, the same panel offers to regenerate.
 *
 * Two loading states are handled differently on purpose:
 *
 * * the **first** generation replaces the (absent) answer with a shimmer skeleton
 *   and the button reports progress, because there is nothing to look at yet;
 * * a **regeneration** keeps the current answer on screen but dims it and marks the
 *   panel busy, because replacing text with a placeholder would throw away
 *   information the user is reading. The new text fades in when it arrives.
 *
 * State resets by remount: the parent passes a `key` derived from the subject, which
 * is the idiomatic alternative to resetting state inside an effect.
 *
 * Everything we know about provenance is shown on purpose: which provider answered,
 * whether it was degraded, whether it came from the store, and how many comments the
 * text was based on.
 */
export function InsightPanel({ seriesId, episodeId, commentCount }: InsightPanelProps) {
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  // Bumped on every answer so the entrance animation replays even when two
  // consecutive answers happen to have identical provenance.
  const [revision, setRevision] = useState(0);

  const load = useCallback(
    async (refresh: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const result = episodeId
          ? await api.episodeInsight(seriesId, episodeId, refresh)
          : await api.seriesInsight(seriesId, refresh);
        setInsight(result);
        setRevision((current) => current + 1);
      } catch (caught) {
        setError(caught);
      } finally {
        setLoading(false);
      }
    },
    [seriesId, episodeId],
  );

  const regenerating = loading && insight !== null;

  return (
    <section
      aria-labelledby="insight-heading"
      aria-busy={loading}
      data-testid="insight-panel"
      className={`rounded-xl border border-accent/30 bg-accent/5 p-4 transition-shadow duration-300 ${
        loading ? "ring-1 ring-accent/40" : "ring-0"
      }`}
    >
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="insight-heading" className="flex items-center gap-2 font-semibold">
          <span aria-hidden="true">✨</span> AI insight
        </h2>

        {insight ? (
          <button
            type="button"
            data-testid="insight-regenerate"
            onClick={() => void load(true)}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md border border-line px-2.5 py-1 text-xs hover:bg-card-hover disabled:cursor-wait disabled:opacity-70"
          >
            {regenerating ? (
              <Spinner size="sm" label="Regenerating…" />
            ) : (
              "Regenerate"
            )}
          </button>
        ) : null}
      </header>

      <div className="mt-3 text-sm leading-relaxed">
        {error ? <ErrorNotice error={error} onRetry={() => void load(true)} /> : null}

        {/*
          Always present so screen readers are listening before the answer arrives.
          `aria-busy` on the section makes them wait for the settled content.
        */}
        <div aria-live="polite">
          {insight ? (
            <p
              key={revision}
              data-testid="insight-text"
              className={`animate-fade-up transition-opacity duration-300 ${
                regenerating ? "opacity-40" : "opacity-100"
              }`}
            >
              {insight.text}
            </p>
          ) : loading ? (
            <Skeleton lines={3} testId="insight-skeleton" />
          ) : null}
        </div>

        {!insight ? (
          <div className="mt-3 space-y-2">
            <button
              type="button"
              data-testid="insight-generate"
              onClick={() => void load(false)}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-soft disabled:cursor-wait disabled:opacity-70"
            >
              {loading ? (
                <Spinner size="sm" tone="onAccent" label="Generating…" />
              ) : (
                "View insights"
              )}
            </button>
            {loading ? null : (
              <p className="text-xs text-muted">
                Generated on demand from the summary, the genres and{" "}
                {commentCount ?? 0} community comment{commentCount === 1 ? "" : "s"}.
              </p>
            )}
          </div>
        ) : null}
      </div>

      {insight ? (
        <footer
          key={`meta-${revision}`}
          className="animate-fade-up mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted"
        >
          <span
            data-testid="insight-provider"
            className="rounded-full bg-overlay px-2 py-0.5"
          >
            via {insight.provider}
          </span>
          {insight.degraded ? (
            <span className="rounded-full bg-amber-400/15 px-2 py-0.5 text-amber-700 dark:text-amber-200">
              offline fallback
            </span>
          ) : null}
          {insight.cached ? (
            <span
              data-testid="insight-cached"
              className="rounded-full bg-overlay px-2 py-0.5"
            >
              reused
            </span>
          ) : null}
          <span data-testid="insight-basis">
            based on {insight.based_on_comment_count} comment
            {insight.based_on_comment_count === 1 ? "" : "s"}
          </span>
          {commentCount !== undefined &&
          commentCount > insight.based_on_comment_count ? (
            <span
              data-testid="insight-stale"
              className="rounded-full bg-sky-400/15 px-2 py-0.5 text-sky-700 dark:text-sky-200"
            >
              {commentCount - insight.based_on_comment_count} new comment
              {commentCount - insight.based_on_comment_count === 1 ? "" : "s"} since this
              insight
            </span>
          ) : null}
        </footer>
      ) : null}
    </section>
  );
}
