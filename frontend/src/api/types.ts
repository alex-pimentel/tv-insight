/**
 * The API contract, derived from the backend's OpenAPI document.
 *
 * `schema.d.ts` is generated (`make client`) from `openapi.json`, which the
 * backend dumps from its own FastAPI app (`make openapi`). This module only gives
 * the generated schemas stable, readable names, so the wire format has a single
 * source of truth instead of two hand-synchronised files.
 *
 * The response properties are required in the generated types because the server
 * always emits every field (`null` when absent); request bodies keep their real
 * optionality. See `scripts/generate-api.mjs` for the exact rule.
 */

import type { components } from "./schema";

type Schemas = components["schemas"];

export type SeriesCard = Schemas["SeriesCardModel"];
export type Episode = Schemas["EpisodeModel"];
export type Season = Schemas["SeasonModel"];
export type Comment = Schemas["CommentModel"];
export type SearchResponse = Schemas["SearchResponse"];
export type SeriesDetail = Schemas["SeriesDetailModel"];
export type EpisodeDetail = Schemas["EpisodeDetailModel"];
export type Insight = Schemas["InsightsResponse"];
export type Session = Schemas["SessionModel"];
export type ProviderStatus = Schemas["ProviderStatus"];
export type Health = Schemas["HealthModel"];
export type ApiErrorBody = Schemas["ErrorModel"];
