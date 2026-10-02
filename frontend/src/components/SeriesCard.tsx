import { Link } from "react-router-dom";
import type { SeriesCard as SeriesCardModel } from "../api/types";

interface SeriesCardProps {
  series: SeriesCardModel;
}

/** One search result: poster, title, year and genres. */
export function SeriesCard({ series }: SeriesCardProps) {
  // The grid shows many small cards, so it downloads the `medium` image and only
  // falls back to the original if the catalogue did not publish a smaller one.
  const poster = series.poster_thumbnail_url ?? series.poster_url;

  return (
    <Link
      to={`/series/${series.id}`}
      data-testid="series-card"
      className="group flex flex-col overflow-hidden rounded-xl border border-line bg-card transition hover:border-accent/60 hover:bg-card-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
    >
      <div className="aspect-[2/3] w-full overflow-hidden bg-card-hover">
        {poster ? (
          <img
            src={poster}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-3xl text-muted">
            🎬
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <h3 className="line-clamp-2 font-semibold leading-tight">{series.name}</h3>
        <p className="text-xs text-muted">
          {series.year ?? "—"}
          {series.network ? ` · ${series.network}` : ""}
          {series.rating !== null ? ` · ★ ${series.rating}` : ""}
        </p>
        {series.genres.length > 0 ? (
          <ul className="mt-1 flex flex-wrap gap-1">
            {series.genres.slice(0, 3).map((genre) => (
              <li
                key={genre}
                className="rounded-full bg-overlay px-2 py-0.5 text-[11px] text-ink"
              >
                {genre}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Link>
  );
}
