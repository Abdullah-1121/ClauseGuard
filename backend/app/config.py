"""Application settings, loaded from environment / .env.

All model access is configured here so provider/model choice is never hard-coded
in the pipeline. See `app.providers.factory` for how these are turned into models.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "cerebras", "ollama", "openrouter"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLAUSEGUARD_",
        env_file=".env",
        extra="ignore",
    )

    # Inference
    provider: Provider = "groq"
    model_strong: str = "openai/gpt-oss-120b"
    model_cheap: str = "openai/gpt-oss-20b"

    # Provider credentials (non-prefixed, standard env names)
    groq_api_key: str = Field("", validation_alias="GROQ_API_KEY")
    cerebras_api_key: str = Field("", validation_alias="CEREBRAS_API_KEY")
    cerebras_base_url: str = Field(
        "https://api.cerebras.ai/v1", validation_alias="CEREBRAS_BASE_URL"
    )
    openrouter_api_key: str = Field("", validation_alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1", validation_alias="OPENROUTER_BASE_URL"
    )
    ollama_base_url: str = Field("http://localhost:11434/v1", validation_alias="OLLAMA_BASE_URL")

    # Guardrails
    confidence_threshold: float = 0.55

    # Observability (optional)
    langfuse_public_key: str = Field("", validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field("", validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        "https://cloud.langfuse.com",
        # Accept both our LANGFUSE_HOST name and the SDK-standard
        # LANGFUSE_BASE_URL (what the official docs and .env use).
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )

    # API auth
    api_keys: str = "dev-local-key"  # comma-separated
    rate_limit_per_minute: int = 10

    # Spend protection (for public deploys — a leaked key must not drain the
    # provider quota). 0 disables each guard.
    daily_token_budget: int = 0
    max_review_chars: int = 100_000

    # Job store
    db_path: str = "clauseguard.db"

    @property
    def allowed_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def observability_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
