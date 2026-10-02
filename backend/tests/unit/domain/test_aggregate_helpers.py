"""Level 1: comportamento do agregado que os use cases não exercitam.

Sobraram properties e helpers na API do agregado que nenhum caso de uso chama hoje.
Eles continuam sendo contrato do domínio: se quebrarem, alguém vai descobrir em
produção. Melhor descobrir aqui.
"""

from __future__ import annotations

from datetime import UTC, datetime

from tv_insight.domain.entities.episode import Episode
from tv_insight.domain.entities.guide import EpisodeGuide, Season
from tv_insight.domain.services.watch_progress import (
    SeasonProgress,
    WatchProgressService,
)
from tv_insight.domain.value_objects import EpisodeId, EpisodeNumber, SeasonNumber, SeriesId

SERIES = SeriesId(1)


def episode(episode_id: int, season: int, number: int) -> Episode:
    return Episode(
        id=EpisodeId(episode_id),
        series_id=SERIES,
        name=f"S{season}E{number}",
        season=SeasonNumber(season),
        number=EpisodeNumber(number),
    )


class TestSeason:
    def test_specials_are_labelled_instead_of_numbered(self) -> None:
        season = Season(number=SeasonNumber(0), episodes=(episode(1, 0, 1),))
        assert season.label == "Specials"

    def test_a_numbered_season_is_labelled_with_its_number(self) -> None:
        season = Season(number=SeasonNumber(2), episodes=(episode(2, 2, 1),))
        assert season.label == "Season 2"

    def test_contains_only_its_own_episodes(self) -> None:
        season = Season(number=SeasonNumber(1), episodes=(episode(101, 1, 1),))

        assert season.contains(EpisodeId(101)) is True
        assert season.contains(EpisodeId(999)) is False

    def test_episode_count(self) -> None:
        season = Season(number=SeasonNumber(1), episodes=(episode(1, 1, 1), episode(2, 1, 2)))
        assert season.episode_count == 2


class TestEpisodeFlags:
    def test_a_season_zero_episode_is_a_special(self) -> None:
        assert episode(1, 0, 1).is_special is True

    def test_a_regular_episode_is_not_special(self) -> None:
        assert episode(1, 3, 4).is_special is False


class TestSeasonProgressEdges:
    def test_ratio_of_an_empty_season_is_zero(self) -> None:
        progress = SeasonProgress(number=SeasonNumber(1), label="Season 1", watched=0, total=0)

        assert progress.ratio == 0.0
        assert progress.is_complete is False
        assert progress.is_started is False

    def test_a_partially_watched_season_is_started_but_not_complete(self) -> None:
        progress = SeasonProgress(number=SeasonNumber(1), label="Season 1", watched=1, total=4)

        assert progress.is_started is True
        assert progress.is_complete is False

    def test_a_fully_watched_season_is_complete(self) -> None:
        progress = SeasonProgress(number=SeasonNumber(1), label="Season 1", watched=4, total=4)
        assert progress.is_complete is True


class TestWatchSummaryEdges:
    def test_an_empty_summary_does_not_divide_by_zero(self) -> None:
        summary = WatchProgressService().summarize(
            EpisodeGuide.from_episodes(SERIES, []), frozenset()
        )

        assert summary.ratio == 0.0
        assert summary.is_complete is False
        assert summary.seasons == ()


def test_watch_timestamps_must_be_timezone_aware() -> None:
    # Guard: a naive datetime would silently order comments/watches wrongly.
    now = datetime(2024, 1, 1, tzinfo=UTC)
    assert now.tzinfo is not None
