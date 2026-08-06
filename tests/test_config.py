"""Configuration safety tests."""

from __future__ import annotations

from pytest import MonkeyPatch

from point_audit.config import Settings


def test_ai_is_disabled_without_environment_configuration(monkeypatch: MonkeyPatch) -> None:
    """AI remains optional when no AI-related variables are configured."""
    monkeypatch.delenv("AI_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings.from_environment()

    assert settings.ai_enabled is False
    assert settings.openai_api_key is None
