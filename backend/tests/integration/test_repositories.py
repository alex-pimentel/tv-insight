"""Level 3: the SQLAlchemy repositories and the unit of work.

These exercise the real database. They are skipped automatically when no
database is reachable, so ``pytest`` still works on a laptop with nothing running,
but the CI pipeline (and ``make test-integration``) runs them for real.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine

from tv_insight.domain.entities.comments import Comment
from tv_insight.domain.entities.insight import StoredInsight
from tv_insight.domain.entities.watch import WatchedEpisode
from tv_insight.domain.value_objects import (
    CommentText,
    ContentTarget,
    EpisodeId,
    SeriesId,
    ViewerId,
)
from tv_insight.infrastructure.config import Settings
from tv_insight.infrastructure.db.models import (
    CommentRow,
    InsightRow,
    WatchedEpisodeRow,
)
from tv_insight.infrastructure.db.session import (
    create_engine,
    create_session_factory,
    ping,
)
from tv_insight.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration

NOW = datetime(2024, 5, 1, 12, 0, tzinfo=UTC)
SERIES = SeriesId(101)
OTHER_SERIES = SeriesId(202)
VIEWER = ViewerId("viewer-a")
OTHER_VIEWER = ViewerId("viewer-b")


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    settings = Settings()
    candidate = create_engine(settings)
    if not await ping(candidate):
        await candidate.dispose()
        pytest.skip("no database reachable; start docker compose to run this suite")
        return

    async with candidate.begin() as connection:
        await connection.execute(delete(CommentRow))
        await connection.execute(delete(WatchedEpisodeRow))
        await connection.execute(delete(InsightRow))

    yield candidate
    await candidate.dispose()


@pytest_asyncio.fixture
async def uow(engine: AsyncEngine) -> AsyncIterator[SqlAlchemyUnitOfWork]:
    session_factory = create_session_factory(engine)
    yield SqlAlchemyUnitOfWork(session_factory)


def _comment(
    identifier: str,
    *,
    target: ContentTarget,
    series: SeriesId = SERIES,
    episode: EpisodeId | None = None,
    viewer: ViewerId = VIEWER,
    text: str = "A comment",
    created_at: datetime = NOW,
) -> Comment:
    return Comment(
        id=identifier,
        viewer_id=viewer,
        target=target,
        series_id=series,
        episode_id=episode,
        text=CommentText(text),
        created_at=created_at,
    )


class TestCommentRepository:
    async def test_add_and_read_a_series_comment(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.comments.add(
                _comment("c1", target=ContentTarget.SERIES, text="Hello")
            )
            await uow.commit()

        async with uow:
            rows = await uow.comments.list_for_series(SERIES)

        assert [row.text.value for row in rows] == ["Hello"]
        assert rows[0].target is ContentTarget.SERIES
        assert rows[0].created_at.tzinfo is not None

    async def test_episode_comments_are_scoped_to_the_episode(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.comments.add(
                _comment(
                    "c1",
                    target=ContentTarget.EPISODE,
                    episode=EpisodeId(1),
                    text="episode one",
                )
            )
            await uow.comments.add(
                _comment(
                    "c2",
                    target=ContentTarget.EPISODE,
                    episode=EpisodeId(2),
                    text="episode two",
                )
            )
            await uow.commit()

        async with uow:
            rows = await uow.comments.list_for_episode(EpisodeId(1))

        assert [row.text.value for row in rows] == ["episode one"]

    async def test_series_and_episode_comments_do_not_mix(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.comments.add(
                _comment("c1", target=ContentTarget.SERIES, text="series level")
            )
            await uow.comments.add(
                _comment(
                    "c2",
                    target=ContentTarget.EPISODE,
                    episode=EpisodeId(1),
                    text="episode level",
                )
            )
            await uow.commit()

        async with uow:
            series_rows = await uow.comments.list_for_series(SERIES)

        assert [row.text.value for row in series_rows] == ["series level"]

    async def test_newest_first_ordering(self, uow: SqlAlchemyUnitOfWork) -> None:
        async with uow:
            for index in range(3):
                await uow.comments.add(
                    _comment(
                        f"c{index}",
                        target=ContentTarget.SERIES,
                        text=f"comment {index}",
                        created_at=NOW + timedelta(minutes=index),
                    )
                )
            await uow.commit()

        async with uow:
            rows = await uow.comments.list_for_series(SERIES)

        assert [row.text.value for row in rows] == ["comment 2", "comment 1", "comment 0"]

    async def test_limit_is_applied(self, uow: SqlAlchemyUnitOfWork) -> None:
        async with uow:
            for index in range(5):
                await uow.comments.add(
                    _comment(f"c{index}", target=ContentTarget.SERIES)
                )
            await uow.commit()

        async with uow:
            rows = await uow.comments.list_for_series(SERIES, limit=2)

        assert len(rows) == 2

    async def test_counts(self, uow: SqlAlchemyUnitOfWork) -> None:
        async with uow:
            await uow.comments.add(_comment("c1", target=ContentTarget.SERIES))
            await uow.comments.add(_comment("c2", target=ContentTarget.SERIES))
            await uow.comments.add(
                _comment("c3", target=ContentTarget.EPISODE, episode=EpisodeId(9))
            )
            await uow.commit()

        async with uow:
            assert await uow.comments.count_for_series(SERIES) == 2
            assert await uow.comments.count_for_episode(EpisodeId(9)) == 1
            assert await uow.comments.count_for_series(OTHER_SERIES) == 0

    async def test_rollback_discards_writes(self, engine: AsyncEngine) -> None:
        session_factory = create_session_factory(engine)
        uow = SqlAlchemyUnitOfWork(session_factory)

        with pytest.raises(RuntimeError):
            async with uow:
                await uow.comments.add(_comment("c1", target=ContentTarget.SERIES))
                raise RuntimeError("boom")

        async with SqlAlchemyUnitOfWork(session_factory) as fresh:
            assert await fresh.comments.count_for_series(SERIES) == 0


class TestWatchedRepository:
    async def test_save_exists_and_remove(self, uow: SqlAlchemyUnitOfWork) -> None:
        episode = EpisodeId(55)
        record = WatchedEpisode(
            viewer_id=VIEWER,
            series_id=SERIES,
            episode_id=episode,
            watched_at=NOW,
        )

        async with uow:
            await uow.watches.save(record)
            await uow.commit()

        async with uow:
            assert await uow.watches.exists(VIEWER, episode) is True
            assert await uow.watches.exists(OTHER_VIEWER, episode) is False

        async with uow:
            await uow.watches.remove(VIEWER, episode)
            await uow.commit()

        async with uow:
            assert await uow.watches.exists(VIEWER, episode) is False

    async def test_save_is_idempotent(self, uow: SqlAlchemyUnitOfWork) -> None:
        episode = EpisodeId(55)
        record = WatchedEpisode(
            viewer_id=VIEWER, series_id=SERIES, episode_id=episode, watched_at=NOW
        )

        async with uow:
            await uow.watches.save(record)
            await uow.watches.save(record)
            await uow.commit()

        async with uow:
            ids = await uow.watches.list_episode_ids(VIEWER, SERIES)

        assert ids == frozenset({episode})

    async def test_removing_something_absent_is_a_no_op(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.watches.remove(VIEWER, EpisodeId(999))
            await uow.commit()

        async with uow:
            assert await uow.watches.list_episode_ids(VIEWER, SERIES) == frozenset()

    async def test_progress_is_scoped_by_series_and_viewer(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            for episode in (1, 2, 3):
                await uow.watches.save(
                    WatchedEpisode(
                        viewer_id=VIEWER,
                        series_id=SERIES,
                        episode_id=EpisodeId(episode),
                        watched_at=NOW,
                    )
                )
            await uow.watches.save(
                WatchedEpisode(
                    viewer_id=VIEWER,
                    series_id=OTHER_SERIES,
                    episode_id=EpisodeId(99),
                    watched_at=NOW,
                )
            )
            await uow.watches.save(
                WatchedEpisode(
                    viewer_id=OTHER_VIEWER,
                    series_id=SERIES,
                    episode_id=EpisodeId(4),
                    watched_at=NOW,
                )
            )
            await uow.commit()

        async with uow:
            ids = await uow.watches.list_episode_ids(VIEWER, SERIES)

        assert ids == frozenset({EpisodeId(1), EpisodeId(2), EpisodeId(3)})


class TestInsightRepository:
    """The durable insight store: the cache the client asked for."""

    @staticmethod
    def _insight(
        *,
        target: ContentTarget = ContentTarget.SERIES,
        target_id: int = 169,
        text: str = "A curated insight.",
        based_on: int = 3,
    ) -> StoredInsight:
        return StoredInsight(
            target=target,
            target_id=target_id,
            text=text,
            provider="heuristic",
            degraded=True,
            based_on_comment_count=based_on,
            generated_at=NOW,
        )

    async def test_an_unknown_subject_has_no_insight(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            assert await uow.insights.get(ContentTarget.SERIES, 424242) is None

    async def test_save_and_read_back_every_field(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.insights.save(self._insight(text="Hello there", based_on=4))
            await uow.commit()

        async with uow:
            stored = await uow.insights.get(ContentTarget.SERIES, 169)

        assert stored is not None
        assert stored.text == "Hello there"
        assert stored.provider == "heuristic"
        assert stored.degraded is True
        assert stored.based_on_comment_count == 4
        assert stored.target is ContentTarget.SERIES
        assert stored.target_id == 169
        assert stored.generated_at.tzinfo is not None

    async def test_saving_twice_replaces_the_row(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.insights.save(self._insight(text="first", based_on=1))
            await uow.commit()

        async with uow:
            await uow.insights.save(self._insight(text="second", based_on=2))
            await uow.commit()

        async with uow:
            stored = await uow.insights.get(ContentTarget.SERIES, 169)

        assert stored is not None
        assert stored.text == "second"
        assert stored.based_on_comment_count == 2

    async def test_series_and_episode_insights_coexist(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.insights.save(self._insight(text="about the series"))
            await uow.insights.save(
                self._insight(
                    target=ContentTarget.EPISODE,
                    target_id=12192,
                    text="about the episode",
                )
            )
            await uow.commit()

        async with uow:
            series = await uow.insights.get(ContentTarget.SERIES, 169)
            episode = await uow.insights.get(ContentTarget.EPISODE, 12192)

        assert series is not None and series.text == "about the series"
        assert episode is not None and episode.text == "about the episode"

    async def test_only_the_insights_table_is_touched(
        self, uow: SqlAlchemyUnitOfWork
    ) -> None:
        async with uow:
            await uow.insights.save(self._insight(text="kept"))
            await uow.commit()

        with pytest.raises(RuntimeError):
            async with uow:
                await uow.comments.add(_comment("rollback-me", target=ContentTarget.SERIES))
                raise RuntimeError("boom")

        async with uow:
            stored = await uow.insights.get(ContentTarget.SERIES, 169)
            comments = await uow.comments.count_for_series(SERIES)

        assert stored is not None and stored.text == "kept"
        assert comments == 0
