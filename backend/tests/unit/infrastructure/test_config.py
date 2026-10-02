"""Level 3: configuration is validated and derived, never read ad hoc."""

from __future__ import annotations

import pytest

from tv_insight.infrastructure.config import KNOWN_PROVIDERS, Settings


def test_database_url_is_assembled_from_parts() -> None:
    settings = Settings(
        postgres_user="u",
        postgres_password="p",
        postgres_host="h",
        postgres_port=5432,
        postgres_db="d",
        database_url=None,
    )
    assert settings.sqlalchemy_url == "postgresql+asyncpg://u:p@h:5432/d"


def test_explicit_database_url_wins() -> None:
    settings = Settings(database_url="postgresql+asyncpg://x:y@z:1/w")
    assert settings.sqlalchemy_url == "postgresql+asyncpg://x:y@z:1/w"


def test_password_is_url_encoded() -> None:
    settings = Settings(
        postgres_user="u", postgres_password="p@ss/word", database_url=None
    )
    assert "p%40ss%2Fword" in settings.sqlalchemy_url


@pytest.mark.parametrize("raw", ["*", "", "   "])
def test_wildcard_cors(raw: str) -> None:
    assert Settings(cors_allow_origins=raw).cors_origins == ["*"]


def test_cors_list_is_split_and_trimmed() -> None:
    settings = Settings(cors_allow_origins="http://a.test, http://b.test")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_provider_order_is_filtered_against_known_names() -> None:
    settings = Settings(ai_provider_order=" HuggingFace , bogus ,heuristic, ")
    assert settings.provider_order == ("huggingface", "heuristic")


def test_known_providers_are_documented() -> None:
    assert set(KNOWN_PROVIDERS) == {"huggingface", "openrouter", "heuristic"}


@pytest.mark.parametrize(
    ("env_name", "expected"),
    [("production", True), ("PROD", True), ("development", False), ("test", False)],
)
def test_is_production(env_name: str, expected: bool) -> None:
    assert Settings(app_env=env_name).is_production is expected


def test_environment_variables_are_picked_up(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PORT", "9999")
    monkeypatch.setenv("AI_PROVIDER_ORDER", "openrouter")

    settings = Settings()

    assert settings.app_port == 9999
    assert settings.provider_order == ("openrouter",)


def test_defaults_are_usable_without_any_configuration() -> None:
    settings = Settings()

    assert settings.app_port == 7777
    # The client chose a primary model plus the local heuristic process; a second
    # model tier is opt-in.
    assert settings.provider_order == ("huggingface", "heuristic")
    assert settings.ai_max_comments == 12
    # 0 = regenerate on every request, and no in-process memoisation: the product
    # wants a fresh generation per click, with the store as the failure fallback.
    assert settings.ai_insight_comment_threshold == 0
    assert settings.ai_insight_cache_ttl_seconds == 0


def test_the_regeneration_threshold_is_configurable() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("AI_INSIGHT_COMMENT_THRESHOLD", "3")
    try:
        assert Settings().ai_insight_comment_threshold == 3
    finally:
        monkeypatch.undo()
