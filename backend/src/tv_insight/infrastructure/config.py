"""Typed, environment driven configuration.

One ``Settings`` object is built at start up and injected everywhere; no module
reads ``os.environ`` on its own. That makes configuration explicit, validated and
trivially overridable in tests.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

KNOWN_PROVIDERS = ("huggingface", "openrouter", "heuristic")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "production"
    app_port: int = 7777
    log_level: str = "INFO"
    cors_allow_origins: str = "*"

    postgres_user: str = "tvinsight"
    postgres_password: str = "tvinsight"
    postgres_db: str = "tvinsight"
    postgres_host: str = "db"
    postgres_port: int = 5432
    database_url: str | None = None

    tvmaze_base_url: str = "https://api.tvmaze.com"
    tvmaze_timeout_seconds: float = 5.0
    tvmaze_cache_ttl_seconds: float = 300.0
    tvmaze_max_retries: int = 2

    ai_provider_order: str = "huggingface,heuristic"
    ai_timeout_seconds: float = 20.0
    ai_max_comments: int = 12
    ai_max_summary_chars: int = 1200
    #: Regenerate the insight as soon as this many new comments exist.
    #: 0 (default) = regenerate on every request: the user asked for a fresh
    #: generation per click, with the stored insight used only when the model
    #: providers fail. Set to 1 to restore the client's earlier cost-control rule.
    ai_insight_comment_threshold: int = 0
    #: In-process memoisation of identical prompts. 0 (default) disables it, so a
    #: request always reaches the provider; a positive TTL absorbs bursts.
    ai_insight_cache_ttl_seconds: float = 0.0

    huggingface_api_token: str = ""
    # Served by the HuggingFace Inference Providers router. The task endpoint
    # (`/hf-inference/models/{model}`) is pinned to one provider and rejects most
    # current models; the OpenAI-compatible endpoint lets the router pick a
    # provider that actually serves the model.
    # Discover valid ids with: GET https://router.huggingface.co/v1/models
    huggingface_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    huggingface_base_url: str = "https://router.huggingface.co/v1"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "http://localhost:7777"
    openrouter_app_name: str = "tv-insight"

    static_dir: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        """Async SQLAlchemy URL. ``DATABASE_URL`` wins when provided."""
        if self.database_url:
            return self.database_url
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def provider_order(self) -> tuple[str, ...]:
        """Configured provider chain, filtered against the known names."""
        names = tuple(
            name.strip().lower() for name in self.ai_provider_order.split(",") if name.strip()
        )
        return tuple(name for name in names if name in KNOWN_PROVIDERS)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process wide singleton (overridden in tests via ``cache_clear``)."""
    return Settings()
