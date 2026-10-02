import type { Comment, Episode, Season, SeriesCard, SeriesDetail } from "../api/types";

export const series: SeriesCard = {
  id: 1,
  name: "Breaking Bad",
  year: 2008,
  poster_url: "https://example.test/bb.jpg",
  poster_thumbnail_url: "https://example.test/bb-thumb.jpg",
  genres: ["Drama", "Crime"],
  status: "Ended",
  rating: 9.2,
  network: "AMC",
  language: "English",
};

function episode(id: number, season: number, number: number, watched = false): Episode {
  return {
    id,
    name: `Episode ${number}`,
    season,
    number,
    code: `S${String(season).padStart(2, "0")}E${String(number).padStart(2, "0")}`,
    summary: `Summary of episode ${number}.`,
    airdate: "2008-01-20",
    runtime_minutes: 47,
    image_url: null,
    watched,
  };
}

export function seasons(watched: number[] = []): Season[] {
  const isWatched = (id: number) => watched.includes(id);
  const build = (season: number, ids: number[]): Season => {
    const episodes = ids.map((id, index) => episode(id, season, index + 1, isWatched(id)));
    const watchedCount = episodes.filter((item) => item.watched).length;
    return {
      number: season,
      label: `Season ${season}`,
      episodes,
      watched: watchedCount,
      total: episodes.length,
      progress: episodes.length === 0 ? 0 : watchedCount / episodes.length,
    };
  };
  return [build(1, [101, 102]), build(2, [201, 202])];
}

export function seriesDetail(watched: number[] = []): SeriesDetail {
  const list = seasons(watched);
  const total = list.reduce((sum, season) => sum + season.episodes.length, 0);
  const watchedCount = list.reduce(
    (sum, season) => sum + season.episodes.filter((item) => item.watched).length,
    0,
  );
  return {
    series,
    summary: "A chemistry teacher turns to crime.",
    seasons: list,
    watched: watchedCount,
    total_episodes: total,
    progress: total === 0 ? 0 : watchedCount / total,
    comment_count: 1,
    comments: [comment()],
  };
}

export function comment(overrides: Partial<Comment> = {}): Comment {
  return {
    id: "c1",
    target: "series",
    series_id: 1,
    episode_id: null,
    episode_code: null,
    text: "Superb writing",
    created_at: "2024-01-01T12:00:00Z",
    author: "Anonymous viewer",
    mine: true,
    ...overrides,
  };
}
