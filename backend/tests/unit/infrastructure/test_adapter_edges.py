"""Level 3: bordas dos adapters — payload inesperado, coerções e ciclo de vida."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import respx

from tv_insight.application.errors import ExternalServiceError
from tv_insight.application.ports.clock import SystemClock
from tv_insight.domain.value_objects import SearchTerm, SeriesId
from tv_insight.infrastructure.config import Settings
from tv_insight.infrastructure.db.session import create_engine, create_session_factory
from tv_insight.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from tv_insight.infrastructure.tvmaze.client import HttpTvMazeGateway
from tv_insight.infrastructure.tvmaze.mappers import _as_int

BASE = "https://edge.test"


class TestTimestampPort:
    def test_the_system_clock_is_timezone_aware(self) -> None:
        now = SystemClock().now()

        assert now.tzinfo is not None
        assert abs((datetime.now(UTC) - now).total_seconds()) < 5


class TestPayloadCoercion:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (7, 7),
            ("7", 7),
            ("-3", -3),
            ("", None),
            ("abc", None),
            (None, None),
            (7.5, None),
            (True, None),  # bool é subclasse de int: nunca deve virar número
        ],
    )
    def test_as_int_is_deliberate_about_what_it_accepts(
        self, raw: object, expected: int | None
    ) -> None:
        assert _as_int(raw) == expected


class TestUnexpectedPayloads:
    """A TVMaze pode responder um formato inesperado (versão nova, gateway no meio)."""

    @respx.mock
    async def test_search_with_a_non_list_payload(self) -> None:
        respx.get(f"{BASE}/search/shows").mock(
            return_value=httpx.Response(200, json={"unexpected": "object"})
        )
        gateway = HttpTvMazeGateway(base_url=BASE)

        with pytest.raises(ExternalServiceError) as error:
            await gateway.search(SearchTerm("dark"))

        assert "Unexpected TVMaze search payload" in str(error.value)

    @respx.mock
    async def test_show_with_a_non_object_payload(self) -> None:
        respx.get(f"{BASE}/shows/1").mock(return_value=httpx.Response(200, json=[1, 2, 3]))
        gateway = HttpTvMazeGateway(base_url=BASE)

        with pytest.raises(ExternalServiceError) as error:
            await gateway.get_series(SeriesId(1))

        assert "Unexpected TVMaze show payload" in str(error.value)

    @respx.mock
    async def test_episodes_with_a_non_list_payload(self) -> None:
        respx.get(f"{BASE}/shows/1/episodes").mock(
            return_value=httpx.Response(200, json="nope")
        )
        gateway = HttpTvMazeGateway(base_url=BASE)

        with pytest.raises(ExternalServiceError) as error:
            await gateway.get_episodes(SeriesId(1))

        assert "Unexpected TVMaze episodes payload" in str(error.value)

    @respx.mock
    async def test_rows_that_are_not_objects_are_skipped_not_fatal(self) -> None:
        respx.get(f"{BASE}/shows/1/episodes").mock(
            return_value=httpx.Response(
                200,
                json=[
                    "a stray string",
                    {"id": 11, "name": "Pilot", "season": 1, "number": 1},
                ],
            )
        )
        gateway = HttpTvMazeGateway(base_url=BASE)

        guide = await gateway.get_episodes(SeriesId(1))

        assert guide.total_episodes == 1

    @respx.mock
    async def test_search_rows_without_a_show_are_skipped(self) -> None:
        respx.get(f"{BASE}/search/shows").mock(
            return_value=httpx.Response(
                200,
                json=[{"score": 1.0, "show": {"id": 5, "name": "Dark"}}, {"score": 0.1}],
            )
        )
        gateway = HttpTvMazeGateway(base_url=BASE)

        results = await gateway.search(SearchTerm("dark"))

        assert [series.name for series in results] == ["Dark"]


class TestUnitOfWorkLifecycle:
    def test_the_unit_can_be_built_without_connecting(self) -> None:
        """Construir o UoW não deve tocar a rede: o engine é lazy."""
        engine = create_engine(
            Settings(database_url="postgresql+asyncpg://u:p@127.0.0.1:1/none")
        )

        unit = SqlAlchemyUnitOfWork(create_session_factory(engine))

        assert unit is not None

    async def test_commit_and_rollback_delegate_to_the_session(self) -> None:
        session = AsyncMock()
        unit = SqlAlchemyUnitOfWork(MagicMock(return_value=session))

        async with unit:
            await unit.commit()
            await unit.rollback()

        session.commit.assert_awaited_once()
        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()

    async def test_an_exception_rolls_the_session_back(self) -> None:
        session = AsyncMock()
        unit = SqlAlchemyUnitOfWork(MagicMock(return_value=session))

        with pytest.raises(RuntimeError):
            async with unit:
                raise RuntimeError("boom")

        session.rollback.assert_awaited_once()
        session.close.assert_awaited_once()
        session.commit.assert_not_awaited()
