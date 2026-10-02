/**
 * The API contract, mirrored by `presentation/api/schemas.py`.
 *
 * Keeping the two in sync is deliberate and cheap for a project this size; the
 * alternative (generating the client from the OpenAPI document) would be the next
 * step and is noted in docs/TRADE-OFFS.md.
 */

export interface SeriesCard {
  id: number;
  name: string;
  year: number | null;
  poster_url: string | null;
  poster_thumbnail_url: string | null;
  genres: string[];
  status: string | null;
  rating: number | null;
  network: string | null;
  language: string | null;
}

export interface Episode {
  id: number;
  name: string;
  season: number;
  number: number;
  code: string;
  summary: string;
  airdate: string | null;
  runtime_minutes: number | null;
  image_url: string | null;
  watched: boolean;
}

export interface Season {
  number: number;
  label: string;
  episodes: Episode[];
  watched: number;
  total: number;
  progress: number;
}

export interface Comment {
  id: string;
  target: "series" | "episode";
  series_id: number;
  episode_id: number | null;
  episode_code: string | null;
  text: string;
  created_at: string;
  author: string;
  mine: boolean;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SeriesCard[];
}

export interface SeriesDetail {
  series: SeriesCard;
  summary: string;
  seasons: Season[];
  watched: number;
  total_episodes: number;
  progress: number;
  comment_count: number;
  comments: Comment[];
}

export interface EpisodeDetail {
  series: SeriesCard;
  episode: Episode;
  comment_count: number;
  comments: Comment[];
  next_episode: Episode | null;
}

export interface Insight {
  text: string;
  provider: string;
  degraded: boolean;
  cached: boolean;
  generated_at: string | null;
  target: string;
  target_id: number;
  based_on_comment_count: number;
  notes: string[];
}

export interface Session {
  kind: string;
}

export interface ProviderStatus {
  provider: string;
  available: boolean;
  /** The configured model, when the provider has one. */
  model?: string | null;
}

export interface Health {
  status: string;
  version: string;
  database: string;
  insights: ProviderStatus[];
}

export interface ApiErrorBody {
  error: string;
  detail?: string | null;
}
