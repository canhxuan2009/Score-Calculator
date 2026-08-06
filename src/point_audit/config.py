"""Environment-backed application configuration."""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Settings(BaseModel):
    """Validated settings that keep AI disabled unless explicitly enabled."""

    model_config = ConfigDict(frozen=True)

    ai_enabled: bool = False
    openai_api_key: SecretStr | None = Field(default=None, repr=False)

    @classmethod
    def from_environment(cls) -> Settings:
        """Load supported settings from environment variables."""
        raw_key = os.getenv("OPENAI_API_KEY")
        return cls.model_validate(
            {
                "ai_enabled": os.getenv("AI_ENABLED", "false"),
                "openai_api_key": raw_key if raw_key else None,
            }
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one immutable settings instance for the current process."""
    return Settings.from_environment()
