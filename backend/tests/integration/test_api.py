"""Level 4: the HTTP interface, exercised end to end in-process.

``httpx.ASGITransport`` drives the real ASGI app (routing, validation, error
handlers, cookie handling) with the external world faked. No server, no network,
no database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from tests.conftest import SERIES_ID
from tests.fakes import (
    FixedClock,
    InMemoryTvMazeGateway,
    InMemoryUnitOfWork,
    ScriptedInsightProvider,
)
from tests.fakes.container import build_test_container
from tv_insight.presentation.api.dependencies import VIEWER_COOKIE
from tv_insight.presentation.app import create_app


@pytest_asyncio.fixture
async def client(
    gateway: InMemoryTvMazeGateway,
    unit_of_work: InMemoryUnitOfWork,
    insight_provider: ScriptedInsightProvider,
    clock: FixedClock,
) -> AsyncIterator[httpx.AsyncClient]:
    container = build_test_container(
        gateway=gateway,
        unit_of_work=unit_of_work,
        provider=insight_provider,
        clock=clock,
    )
    app = create_app(container.settings, container)
    # The ASGI transport does not run the lifespan, so seed the state directly.
    app.state.container = container

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


class TestSearch:
    async def test_search_returns_cards(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/series/search", params={"q": "breaking"})

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        card = body["results"][0]
        assert card["name"] == "Breaking Bad"
        assert card["year"] == 2008
        assert card["poster_url"] == "https://example.test/bb.jpg"
        assert card["poster_thumbnail_url"] == "https://example.test/bb-thumb.jpg"

    async def test_short_query_is_a_400(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/series/search", params={"q": "b"})

        assert response.status_code == 400
        assert response.json()["error"] == "InvalidInput"

    async def test_missing_query_is_a_422(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/series/search")
        assert response.status_code == 422

    async def test_no_match_returns_empty_list(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/series/search", params={"q": "zzzz"})

        assert response.status_code == 200
        assert response.json()["results"] == []


class TestSeriesDetail:
    async def test_detail_contains_seasons_and_comments(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get(f"/api/series/{SERIES_ID.value}")

        assert response.status_code == 200
        body = response.json()
        assert body["series"]["name"] == "Breaking Bad"
        assert body["total_episodes"] == 4
        assert [season["number"] for season in body["seasons"]] == [1, 2]
        assert body["seasons"][0]["label"] == "Season 1"
        assert body["progress"] == 0.0

    async def test_unknown_series_is_a_404(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/series/424242")

        assert response.status_code == 404
        assert response.json()["error"] == "ResourceNotFound"

    async def test_a_viewer_cookie_is_issued(self, client: httpx.AsyncClient) -> None:
        response = await client.get(f"/api/series/{SERIES_ID.value}")
        assert VIEWER_COOKIE in response.cookies or VIEWER_COOKIE in client.cookies


class TestWatching:
    async def test_marking_is_visible_on_the_next_read(
        self, client: httpx.AsyncClient
    ) -> None:
        first = await client.get(f"/api/series/{SERIES_ID.value}")
        assert first.json()["watched"] == 0

        marked = await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/101/watched",
            json={"watched": True},
        )
        assert marked.status_code == 200
        assert marked.json()["watched"] is True

        second = await client.get(f"/api/series/{SERIES_ID.value}")
        body = second.json()
        assert body["watched"] == 1
        assert body["progress"] == 0.25
        assert body["seasons"][0]["episodes"][0]["watched"] is True

    async def test_unmarking_is_visible_on_the_next_read(
        self, client: httpx.AsyncClient
    ) -> None:
        await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/101/watched", json={"watched": True}
        )
        await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/101/watched", json={"watched": False}
        )

        body = (await client.get(f"/api/series/{SERIES_ID.value}")).json()

        assert body["watched"] == 0
        assert body["seasons"][0]["episodes"][0]["watched"] is False

    async def test_unknown_episode_is_a_404(self, client: httpx.AsyncClient) -> None:
        response = await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/999999/watched",
            json={"watched": True},
        )
        assert response.status_code == 404

    async def test_watch_state_is_scoped_to_the_cookie(
        self, client: httpx.AsyncClient
    ) -> None:
        await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/101/watched", json={"watched": True}
        )

        client.cookies.set(VIEWER_COOKIE, "another-viewer")
        body = (await client.get(f"/api/series/{SERIES_ID.value}")).json()

        assert body["watched"] == 0


class TestEpisodeDetail:
    async def test_episode_detail_includes_next_episode(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get(f"/api/series/{SERIES_ID.value}/episodes/101")

        assert response.status_code == 200
        body = response.json()
        assert body["episode"]["code"] == "S01E01"
        assert body["next_episode"]["code"] == "S01E02"

    async def test_last_episode_has_no_successor(
        self, client: httpx.AsyncClient
    ) -> None:
        body = (await client.get(f"/api/series/{SERIES_ID.value}/episodes/202")).json()
        assert body["next_episode"] is None

    async def test_foreign_episode_is_a_404(self, client: httpx.AsyncClient) -> None:
        response = await client.get(f"/api/series/{SERIES_ID.value}/episodes/987654")
        assert response.status_code == 404


class TestComments:
    async def test_create_and_list_a_series_comment(
        self, client: httpx.AsyncClient
    ) -> None:
        created = await client.post(
            f"/api/series/{SERIES_ID.value}/comments", json={"text": "  Masterpiece  "}
        )

        assert created.status_code == 201
        assert created.json()["text"] == "Masterpiece"
        assert created.json()["target"] == "series"

        listed = await client.get(f"/api/series/{SERIES_ID.value}/comments")
        assert [item["text"] for item in listed.json()] == ["Masterpiece"]

    async def test_create_an_episode_comment(self, client: httpx.AsyncClient) -> None:
        created = await client.post(
            f"/api/series/{SERIES_ID.value}/comments",
            json={"text": "That ending", "episode_id": 201},
        )

        body = created.json()
        assert body["target"] == "episode"
        assert body["episode_code"] == "S02E01"

        filtered = await client.get(
            f"/api/series/{SERIES_ID.value}/comments", params={"episode_id": 201}
        )
        assert [item["text"] for item in filtered.json()] == ["That ending"]

    async def test_blank_comment_is_a_422(self, client: httpx.AsyncClient) -> None:
        response = await client.post(
            f"/api/series/{SERIES_ID.value}/comments", json={"text": ""}
        )
        assert response.status_code == 422

    async def test_comment_on_unknown_series_is_a_404(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.post("/api/series/424242/comments", json={"text": "hi"})
        assert response.status_code == 404

    async def test_comment_count_appears_in_the_detail(
        self, client: httpx.AsyncClient
    ) -> None:
        await client.post(
            f"/api/series/{SERIES_ID.value}/comments", json={"text": "Nice"}
        )

        body = (await client.get(f"/api/series/{SERIES_ID.value}")).json()

        assert body["comment_count"] == 1
        assert body["comments"][0]["text"] == "Nice"


class TestInsights:
    async def test_series_insight_reports_its_provider(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get(f"/api/series/{SERIES_ID.value}/insight")

        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "A gritty character study."
        assert body["provider"] == "scripted"
        assert body["degraded"] is False
        assert body["target"] == "series"

    async def test_episode_insight(self, client: httpx.AsyncClient) -> None:
        response = await client.get(
            f"/api/series/{SERIES_ID.value}/episodes/201/insight"
        )

        assert response.status_code == 200
        assert response.json()["target"] == "episode"
        assert response.json()["target_id"] == 201

    async def test_provider_failure_is_a_503(
        self,
        gateway: InMemoryTvMazeGateway,
        unit_of_work: InMemoryUnitOfWork,
    ) -> None:
        from tests.fakes import UnavailableInsightProvider

        container = build_test_container(
            gateway=gateway,
            unit_of_work=unit_of_work,
            provider=UnavailableInsightProvider(),
        )
        app = create_app(container.settings, container)
        app.state.container = container

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as http:
            response = await http.get(f"/api/series/{SERIES_ID.value}/insight")

        assert response.status_code == 503
        assert response.json()["error"] == "ProviderUnavailable"


class TestSession:
    async def test_it_reports_a_guest_session(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/session")

        assert response.status_code == 200
        assert response.json() == {"kind": "guest"}

    async def test_reset_discards_the_identity_and_mints_a_new_one(
        self, client: httpx.AsyncClient
    ) -> None:
        # Any endpoint that needs a viewer mints the guest cookie.
        await client.get(f"/api/series/{SERIES_ID.value}/comments")
        before = client.cookies.get(VIEWER_COOKIE)
        assert before

        response = await client.post("/api/session/reset")

        assert response.status_code == 204
        assert not client.cookies.get(VIEWER_COOKIE)

        await client.get(f"/api/series/{SERIES_ID.value}/comments")
        after = client.cookies.get(VIEWER_COOKIE)

        assert after and after != before

    async def test_a_reset_session_does_not_see_previous_state(
        self, client: httpx.AsyncClient, unit_of_work: InMemoryUnitOfWork
    ) -> None:
        await client.put(
            f"/api/series/{SERIES_ID.value}/episodes/101/watched", json={"watched": True}
        )
        assert (await client.get(f"/api/series/{SERIES_ID.value}")).json()["watched"] == 1

        await client.post("/api/session/reset")

        body = (await client.get(f"/api/series/{SERIES_ID.value}")).json()
        assert body["watched"] == 0


class TestPlatform:
    async def test_health_reports_database_and_providers(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "up"
        assert body["insights"][0]["available"] is True
        # The configured model travels with the status so a stale id is visible
        # without reading the environment (see docs/CLIENT-FEEDBACK.md).
        assert "model" in body["insights"][0]

    async def test_health_is_503_when_the_database_is_down(
        self, gateway: InMemoryTvMazeGateway, unit_of_work: InMemoryUnitOfWork
    ) -> None:
        container = build_test_container(
            gateway=gateway, unit_of_work=unit_of_work, database_ok=False
        )
        app = create_app(container.settings, container)
        app.state.container = container

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as http:
            response = await http.get("/api/health")

        assert response.status_code == 503
        assert response.json()["status"] == "degraded"

    async def test_unknown_api_route_is_json_404(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/nope")

        assert response.status_code == 404
        assert response.json()["error"] == "NotFound"

    async def test_openapi_schema_is_served(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/openapi.json")

        assert response.status_code == 200
        assert "/api/series/search" in response.json()["paths"]

    async def test_openapi_document_describes_errors(self, client: httpx.AsyncClient) -> None:
        document = (await client.get("/api/openapi.json")).json()

        # The shared error responses put the error model in the contract, which is
        # what lets the generated TypeScript client type the failures too.
        assert "ErrorModel" in document["components"]["schemas"]
        responses = document["paths"]["/api/series/{series_id}"]["get"]["responses"]
        assert set(responses) >= {"200", "404", "502"}

    @pytest.mark.parametrize("path", ["/api/docs", "/api-docs", "/docs"])
    async def test_swagger_ui_is_served_from_a_cdn(
        self, client: httpx.AsyncClient, path: str
    ) -> None:
        response = await client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        body = response.text
        # The page reads our document and loads the UI assets from the CDN.
        assert "/api/openapi.json" in body
        assert "cdn.jsdelivr.net/npm/swagger-ui-dist" in body
        assert "swagger-ui" in body
