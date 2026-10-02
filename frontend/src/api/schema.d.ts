export interface paths {
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Liveness and readiness */
        get: operations["health_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Series details */
        get: operations["get_series_detail_api_series__series_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}/comments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List comments */
        get: operations["list_comments_api_series__series_id__comments_get"];
        put?: never;
        /** Add a comment */
        post: operations["add_comment_api_series__series_id__comments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}/episodes/{episode_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Episode details */
        get: operations["get_episode_detail_api_series__series_id__episodes__episode_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}/episodes/{episode_id}/insight": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Insight for an episode */
        get: operations["episode_insight_api_series__series_id__episodes__episode_id__insight_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}/episodes/{episode_id}/watched": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Mark episode */
        put: operations["set_episode_watched_api_series__series_id__episodes__episode_id__watched_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/{series_id}/insight": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Insight for a series */
        get: operations["series_insight_api_series__series_id__insight_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/series/search": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Search TV series */
        get: operations["search_series_api_series_search_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/session": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Describe the current session
         * @description Confirms the session model without exposing the identifier.
         *
         *     The cookie is httpOnly on purpose; the client only needs to know that it is
         *     browsing as a guest.
         */
        get: operations["read_session_api_session_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/session/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Start a new guest session
         * @description Discard the current guest identity.
         *
         *     Deliberately does not mint the replacement here: the next request that needs a
         *     viewer will create one, which keeps the identity logic in a single place
         *     (``dependencies.get_viewer_id``).
         */
        post: operations["reset_session_api_session_reset_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** CommentModel */
        CommentModel: {
            /**
             * Author
             * @default Anonymous viewer
             */
            author: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Episode Code */
            episode_code: string | null;
            /** Episode Id */
            episode_id: number | null;
            /** Id */
            id: string;
            /**
             * Mine
             * @default false
             */
            mine: boolean;
            /** Series Id */
            series_id: number;
            /** Target */
            target: string;
            /** Text */
            text: string;
        };
        /** CommentRequest */
        CommentRequest: {
            /** Episode Id */
            episode_id?: number | null;
            /** Text */
            text: string;
        };
        /** EpisodeDetailModel */
        EpisodeDetailModel: {
            /**
             * Comment Count
             * @default 0
             */
            comment_count: number;
            /** Comments */
            comments: components["schemas"]["CommentModel"][];
            episode: components["schemas"]["EpisodeModel"];
            next_episode: components["schemas"]["EpisodeModel"] | null;
            series: components["schemas"]["SeriesCardModel"];
        };
        /** EpisodeModel */
        EpisodeModel: {
            /** Airdate */
            airdate: string | null;
            /** Code */
            code: string;
            /** Id */
            id: number;
            /** Image Url */
            image_url: string | null;
            /** Name */
            name: string;
            /** Number */
            number: number;
            /** Runtime Minutes */
            runtime_minutes: number | null;
            /** Season */
            season: number;
            /** Summary */
            summary: string;
            /**
             * Watched
             * @default false
             */
            watched: boolean;
        };
        /** ErrorModel */
        ErrorModel: {
            /** Detail */
            detail: string | null;
            /** Error */
            error: string;
        };
        /** HealthModel */
        HealthModel: {
            /** Database */
            database: string;
            /** Insights */
            insights: components["schemas"]["ProviderStatus"][];
            /** Status */
            status: string;
            /** Version */
            version: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail: components["schemas"]["ValidationError"][];
        };
        /** InsightsResponse */
        InsightsResponse: {
            /**
             * Based On Comment Count
             * @default 0
             */
            based_on_comment_count: number;
            /**
             * Cached
             * @default false
             */
            cached: boolean;
            /**
             * Degraded
             * @default false
             */
            degraded: boolean;
            /** Generated At */
            generated_at: string | null;
            /** Notes */
            notes: string[];
            /** Provider */
            provider: string;
            /**
             * Target
             * @default series
             */
            target: string;
            /**
             * Target Id
             * @default 0
             */
            target_id: number;
            /** Text */
            text: string;
        };
        /** ProviderStatus */
        ProviderStatus: {
            /** Available */
            available: boolean;
            /** Model */
            model: string | null;
            /** Provider */
            provider: string;
        };
        /** SearchResponse */
        SearchResponse: {
            /** Count */
            count: number;
            /** Query */
            query: string;
            /** Results */
            results: components["schemas"]["SeriesCardModel"][];
        };
        /** SeasonModel */
        SeasonModel: {
            /** Episodes */
            episodes: components["schemas"]["EpisodeModel"][];
            /** Label */
            label: string;
            /** Number */
            number: number;
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /**
             * Total
             * @default 0
             */
            total: number;
            /**
             * Watched
             * @default 0
             */
            watched: number;
        };
        /** SeriesCardModel */
        SeriesCardModel: {
            /** Genres */
            genres: string[];
            /** Id */
            id: number;
            /** Language */
            language: string | null;
            /** Name */
            name: string;
            /** Network */
            network: string | null;
            /** Poster Thumbnail Url */
            poster_thumbnail_url: string | null;
            /** Poster Url */
            poster_url: string | null;
            /** Rating */
            rating: number | null;
            /** Status */
            status: string | null;
            /** Year */
            year: number | null;
        };
        /** SeriesDetailModel */
        SeriesDetailModel: {
            /**
             * Comment Count
             * @default 0
             */
            comment_count: number;
            /** Comments */
            comments: components["schemas"]["CommentModel"][];
            /**
             * Progress
             * @default 0
             */
            progress: number;
            /** Seasons */
            seasons: components["schemas"]["SeasonModel"][];
            series: components["schemas"]["SeriesCardModel"];
            /** Summary */
            summary: string;
            /**
             * Total Episodes
             * @default 0
             */
            total_episodes: number;
            /**
             * Watched
             * @default 0
             */
            watched: number;
        };
        /** SessionModel */
        SessionModel: {
            /**
             * Kind
             * @default guest
             */
            kind: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx: Record<string, never>;
            /** Input */
            input: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WatchRequest */
        WatchRequest: {
            /**
             * Watched
             * @default true
             */
            watched: boolean;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    get_series_detail_api_series__series_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                series_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SeriesDetailModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    list_comments_api_series__series_id__comments_get: {
        parameters: {
            query?: {
                episode_id?: number | null;
            };
            header?: never;
            path: {
                series_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommentModel"][];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    add_comment_api_series__series_id__comments_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                series_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CommentRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CommentModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    get_episode_detail_api_series__series_id__episodes__episode_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                episode_id: number;
                series_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EpisodeDetailModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    episode_insight_api_series__series_id__episodes__episode_id__insight_get: {
        parameters: {
            query?: {
                /** @description Bypass the insight cache */
                refresh?: boolean;
            };
            header?: never;
            path: {
                episode_id: number;
                series_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InsightsResponse"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    set_episode_watched_api_series__series_id__episodes__episode_id__watched_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                episode_id: number;
                series_id: number;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EpisodeModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    series_insight_api_series__series_id__insight_get: {
        parameters: {
            query?: {
                /** @description Bypass the insight cache */
                refresh?: boolean;
            };
            header?: never;
            path: {
                series_id: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InsightsResponse"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    search_series_api_series_search_get: {
        parameters: {
            query: {
                /** @description Free text query */
                q: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SearchResponse"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    read_session_api_session_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SessionModel"];
                };
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
    reset_session_api_session_reset_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid input */
            400: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Unknown resource */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description Upstream catalogue failure */
            502: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
            /** @description No insight provider available */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorModel"];
                };
            };
        };
    };
}
