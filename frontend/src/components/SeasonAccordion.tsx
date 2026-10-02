import { useState } from "react";
import { Link } from "react-router-dom";
import type { Episode, Season } from "../api/types";
import { ProgressBar } from "./ProgressBar";

interface SeasonAccordionProps {
  seriesId: number;
  seasons: Season[];
  onToggleWatched: (episode: Episode, watched: boolean) => void;
}

export function SeasonAccordion({
  seriesId,
  seasons,
  onToggleWatched,
}: SeasonAccordionProps) {
  const [open, setOpen] = useState<number[]>(() =>
    seasons.length > 0 ? [seasons[0].number] : [],
  );

  const toggle = (seasonNumber: number) =>
    setOpen((current) =>
      current.includes(seasonNumber)
        ? current.filter((value) => value !== seasonNumber)
        : [...current, seasonNumber],
    );

  if (seasons.length === 0) {
    return <p className="text-sm text-muted">No episodes published yet.</p>;
  }

  return (
    <div className="space-y-3" data-testid="season-accordion">
      {seasons.map((season) => {
        const expanded = open.includes(season.number);
        return (
          <section
            key={season.number}
            data-testid="season"
            className="overflow-hidden rounded-xl border border-line bg-card"
          >
            <h3>
              <button
                type="button"
                onClick={() => toggle(season.number)}
                aria-expanded={expanded}
                className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left hover:bg-card-hover"
              >
                <span className="font-medium">
                  {season.label}
                  <span className="ml-2 text-xs text-muted">
                    {season.watched}/{season.total}
                  </span>
                </span>
                <span aria-hidden="true" className="text-muted">
                  {expanded ? "−" : "+"}
                </span>
              </button>
            </h3>

            {expanded ? (
              <div className="border-t border-line">
                <ul>
                  {season.episodes.map((episode) => (
                    <li
                      key={episode.id}
                      data-testid="episode-row"
                      className="flex items-center gap-3 border-b border-line px-4 py-2.5 last:border-b-0"
                    >
                      <label className="flex cursor-pointer items-center gap-3">
                        <input
                          type="checkbox"
                          checked={episode.watched}
                          aria-label={`Mark ${episode.code} ${episode.name} as watched`}
                          onChange={(event) =>
                            onToggleWatched(episode, event.target.checked)
                          }
                          className="h-4 w-4 accent-[var(--accent)]"
                        />
                        <span className="w-14 shrink-0 font-mono text-xs text-muted">
                          {episode.code}
                        </span>
                      </label>

                      <Link
                        to={`/series/${seriesId}/episodes/${episode.id}`}
                        className={`flex-1 truncate text-sm hover:text-accent-soft ${
                          episode.watched ? "text-muted line-through" : ""
                        }`}
                      >
                        {episode.name}
                      </Link>

                      {episode.airdate ? (
                        <time
                          dateTime={episode.airdate}
                          className="hidden text-xs text-muted sm:block"
                        >
                          {episode.airdate}
                        </time>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <div className="bg-overlay px-4 py-2">
                  <ProgressBar
                    value={season.progress}
                    label={`${season.label} progress`}
                  />
                </div>
              </div>
            ) : null}
          </section>
        );
      })}
    </div>
  );
}
