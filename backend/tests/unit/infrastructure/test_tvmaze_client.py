"""Level 3: the TVMaze HTTP adapter, its error mapping and its retry policy."""

from __future__ import annotations

import httpx
import pytest
import respx

from tv_insight.application.errors import ExternalServiceError, ResourceNotFound
from tv_insight.domain.value_objects import SearchTerm, SeriesId
from tv_insight.infrastructure.tvmaze.client import HttpTvMazeGateway

BASE_URL = "https://api.tvmaze.test"

SHOW = {
    "id": 1,
    "name": "Breaking Bad",
    "genres": ["Drama"],
    "image": {"original": "o.jpg"},
    "premiered": "2008-01-20",
}


@pytest.fixture
def gateway() -> HttpTvMazeGateway:
    return HttpTvMazeGateway(base_url=BASE_URL, timeout_seconds=1.0, max_retries=1)


@respx.mock
async def test_search_unwraps_the_show_objects(gateway: HttpTvMazeGateway) -> None:
    respx.get(f"{BASE_URL}/search/shows", params={"q": "breaking"}).mock(
        return_value=httpx.Response(200, json=[{"score": 12.0, "show": SHOW}, {"score": 0.1}])
    )

    results = await gateway.search(SearchTerm("breaking"))

    assert [series.name for series in results] == ["Breaking Bad"]


@respx.mock
async def test_search_with_no_result_is_empty(gateway: HttpTvMazeGateway) -> None:
    respx.get(f"{BASE_URL}/search/shows").mock(return_value=httpx.Response(200, json=[]))
    assert await gateway.search(SearchTerm("zzz")) == ()


@respx.mock
async def test_get_series_maps_the_payload(gateway: HttpTvMazeGateway) -> None:
    respx.get(f"{BASE_URL}/shows/1").mock(return_value=httpx.Response(200, json=SHOW))

    series = await gateway.get_series(SeriesId(1))

    assert series.name == "Breaking Bad"
    assert series.poster_url == "o.jpg"


@respx.mock
async def test_get_episodes_builds_a_guide(gateway: HttpTvMazeGateway) -> None:
    respx.get(f"{BASE_URL}/shows/1/episodes").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 11, "name": "Pilot", "season": 1, "number": 1},
                {"id": 12, "name": "Second", "season": 1, "number": 2},
                {"id": 21, "name": "Next year", "season": 2, "number": 1},
            ],
        )
    )

    guide = await gateway.get_episodes(SeriesId(1))

    assert guide.total_episodes == 3
    assert [season.number.value for season in guide.seasons()] == [1, 2]


@respx.mock
async def test_404_becomes_resource_not_found(gateway: HttpTvMazeGateway) -> None:
    respx.get(f"{BASE_URL}/shows/999").mock(return_value=httpx.Response(404))

    with pytest.raises(ResourceNotFound):
        await gateway.get_series(SeriesId(999))


@respx.mock
async def test_server_error_becomes_external_service_error(
    gateway: HttpTvMazeGateway,
) -> None:
    respx.get(f"{BASE_URL}/shows/1").mock(return_value=httpx.Response(500))

    with pytest.raises(ExternalServiceError):
        await gateway.get_series(SeriesId(1))


@respx.mock
async def test_invalid_json_becomes_external_service_error(
    gateway: HttpTvMazeGateway,
) -> None:
    respx.get(f"{BASE_URL}/shows/1").mock(
        return_value=httpx.Response(200, text="not json")
    )

    with pytest.raises(ExternalServiceError):
        await gateway.get_series(SeriesId(1))


@respx.mock
async def test_malformed_payload_becomes_external_service_error(
    gateway: HttpTvMazeGateway,
) -> None:
    respx.get(f"{BASE_URL}/shows/1").mock(
        return_value=httpx.Response(200, json={"name": "no id"})
    )

    with pytest.raises(ExternalServiceError):
        await gateway.get_series(SeriesId(1))


@respx.mock
async def test_transport_error_is_retried_then_succeeds(
    gateway: HttpTvMazeGateway,
) -> None:
    route = respx.get(f"{BASE_URL}/shows/1").mock(
        side_effect=[httpx.ConnectError("boom"), httpx.Response(200, json=SHOW)]
    )

    series = await gateway.get_series(SeriesId(1))

    assert series.name == "Breaking Bad"
    assert route.call_count == 2


@respx.mock
async def test_persistent_transport_error_becomes_external_service_error(
    gateway: HttpTvMazeGateway,
) -> None:
    respx.get(f"{BASE_URL}/shows/1").mock(side_effect=httpx.ConnectError("down"))

    with pytest.raises(ExternalServiceError):
        await gateway.get_series(SeriesId(1))


@respx.mock
async def test_an_owned_client_is_closed() -> None:
    gateway = HttpTvMazeGateway(base_url=BASE_URL)
    await gateway.aclose()
    assert gateway._client.is_closed is True


@respx.mock
async def test_works_with_an_injected_client_that_has_no_base_url() -> None:
    """Regression: the composition root shares one client across adapters.

    That client is deliberately origin-agnostic, so the gateway must build the
    absolute URL itself instead of relying on ``AsyncClient.base_url``.
    """
    shared = httpx.AsyncClient(timeout=1.0)
    gateway = HttpTvMazeGateway(base_url=BASE_URL, client=shared)
    respx.get(f"{BASE_URL}/shows/1").mock(return_value=httpx.Response(200, json=SHOW))

    try:
        series = await gateway.get_series(SeriesId(1))
    finally:
        await shared.aclose()

    assert series.name == "Breaking Bad"


@respx.mock
async def test_an_injected_client_is_not_closed_by_the_gateway() -> None:
    shared = httpx.AsyncClient(timeout=1.0)
    gateway = HttpTvMazeGateway(base_url=BASE_URL, client=shared)

    await gateway.aclose()

    assert shared.is_closed is False
    await shared.aclose()
