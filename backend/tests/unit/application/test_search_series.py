"""Level 2: search use case with an in-memory gateway."""

from __future__ import annotations

import pytest

from tests.fakes import InMemoryTvMazeGateway
from tv_insight.application.errors import InvalidInput
from tv_insight.application.use_cases import SearchSeries


async def test_search_returns_matching_cards(
    gateway: InMemoryTvMazeGateway,
) -> None:
    results = await SearchSeries(gateway).execute("breaking")

    assert [card.name for card in results] == ["Breaking Bad"]
    assert gateway.search_calls == ["breaking"]


async def test_card_exposes_only_what_the_ui_needs(
    gateway: InMemoryTvMazeGateway,
) -> None:
    card = (await SearchSeries(gateway).execute("breaking"))[0]

    assert card.id == 1
    assert card.year == 2008
    assert card.poster_url == "https://example.test/bb.jpg"
    assert card.poster_thumbnail_url == "https://example.test/bb-thumb.jpg"
    assert card.genres == ("Drama", "Crime")
    assert card.rating == 9.2


async def test_search_is_limited(gateway: InMemoryTvMazeGateway) -> None:
    results = await SearchSeries(gateway, limit=1).execute("be")
    assert len(results) == 1


async def test_no_match_is_an_empty_result_not_an_error(
    gateway: InMemoryTvMazeGateway,
) -> None:
    assert await SearchSeries(gateway).execute("nothing here") == ()


async def test_too_short_query_is_rejected_before_touching_the_gateway(
    gateway: InMemoryTvMazeGateway,
) -> None:
    with pytest.raises(InvalidInput):
        await SearchSeries(gateway).execute("b")

    assert gateway.search_calls == []
