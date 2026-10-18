from __future__ import annotations

import pytest

from app.config import Settings


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("MAX_BATCH_SIZE", "4")
    monkeypatch.setenv("TELEMETRY_ENABLED", "false")
    settings = Settings.from_env()
    assert settings.port == 9000
    assert settings.max_batch_size == 4
    assert settings.telemetry_enabled is False
