import type {
  ApiErrorBody,
  Comment,
  EpisodeDetail,
  Health,
  Insight,
  SearchResponse,
  SeriesDetail,
  Session,
} from "./types";

/** Raised for any non 2xx answer, carrying the server's own error vocabulary. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
    // Required so the http-only viewer cookie travels with every call.
    credentials: "same-origin",
  });

  if (!response.ok) {
    // Declared without an initial value: both branches below assign it, so a
    // `= null` here would be dead.
    let body: ApiErrorBody | null;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(
      response.status,
      body?.error ?? "RequestFailed",
      body?.detail ?? response.statusText,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  search: (query: string, signal?: AbortSignal) =>
    request<SearchResponse>(`/api/series/search?q=${encodeURIComponent(query)}`, {
      signal,
    }),

  seriesDetail: (seriesId: number) =>
    request<SeriesDetail>(`/api/series/${seriesId}`),

  episodeDetail: (seriesId: number, episodeId: number) =>
    request<EpisodeDetail>(`/api/series/${seriesId}/episodes/${episodeId}`),

  setWatched: (seriesId: number, episodeId: number, watched: boolean) =>
    request<unknown>(`/api/series/${seriesId}/episodes/${episodeId}/watched`, {
      method: "PUT",
      body: JSON.stringify({ watched }),
    }),

  listComments: (seriesId: number, episodeId?: number) => {
    const query = episodeId ? `?episode_id=${episodeId}` : "";
    return request<Comment[]>(`/api/series/${seriesId}/comments${query}`);
  },

  addComment: (seriesId: number, text: string, episodeId?: number) =>
    request<Comment>(`/api/series/${seriesId}/comments`, {
      method: "POST",
      body: JSON.stringify({ text, episode_id: episodeId ?? null }),
    }),

  seriesInsight: (seriesId: number, refresh = false) =>
    request<Insight>(`/api/series/${seriesId}/insight${refresh ? "?refresh=true" : ""}`),

  episodeInsight: (seriesId: number, episodeId: number, refresh = false) =>
    request<Insight>(
      `/api/series/${seriesId}/episodes/${episodeId}/insight${refresh ? "?refresh=true" : ""}`,
    ),

  health: () => request<Health>("/api/health"),

  session: () => request<Session>("/api/session"),

  resetSession: () =>
    request<void>("/api/session/reset", { method: "POST" }),
};
