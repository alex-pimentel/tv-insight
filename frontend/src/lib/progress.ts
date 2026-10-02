import type { Episode, Season } from "../api/types";

/**
 * Recomputes season and overall progress after a local change.
 *
 * The server is still the source of truth on the next load; doing the arithmetic
 * here just keeps the UI responsive without a refetch after every checkbox.
 */
export function withEpisodeWatched(
  seasons: Season[],
  episodeId: number,
  watched: boolean,
): Season[] {
  return seasons.map((season) => {
    if (!season.episodes.some((episode) => episode.id === episodeId)) {
      return season;
    }
    const episodes = season.episodes.map((episode) =>
      episode.id === episodeId ? { ...episode, watched } : episode,
    );
    const watchedCount = episodes.filter((episode) => episode.watched).length;
    return {
      ...season,
      episodes,
      watched: watchedCount,
      progress: episodes.length === 0 ? 0 : watchedCount / episodes.length,
    };
  });
}

export function findEpisode(seasons: Season[], episodeId: number): Episode | undefined {
  for (const season of seasons) {
    const match = season.episodes.find((episode) => episode.id === episodeId);
    if (match) return match;
  }
  return undefined;
}

export function overallProgress(seasons: Season[]): {
  watched: number;
  total: number;
  progress: number;
} {
  const total = seasons.reduce((sum, season) => sum + season.episodes.length, 0);
  const watched = seasons.reduce(
    (sum, season) => sum + season.episodes.filter((episode) => episode.watched).length,
    0,
  );
  return { watched, total, progress: total === 0 ? 0 : watched / total };
}
