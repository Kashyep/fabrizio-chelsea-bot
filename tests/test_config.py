from __future__ import annotations

import pytest

from chelsea_bot.config import ConfigurationError, Settings


def test_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "X_BEARER_TOKEN",
        "X_API_KEY",
        "X_API_SECRET",
        "X_ACCESS_TOKEN",
        "X_ACCESS_TOKEN_SECRET",
        "DRY_RUN",
        "BOOTSTRAP_MODE",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.dry_run is True
    assert settings.bootstrap_mode == "baseline"
    assert settings.source_username == "FabrizioRomano"


def test_rejects_invalid_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "perhaps")
    with pytest.raises(ConfigurationError, match="DRY_RUN"):
        Settings.from_env()


def test_live_credentials_are_all_required(settings: Settings) -> None:
    from dataclasses import replace

    incomplete = replace(settings, access_token_secret=None)
    with pytest.raises(ConfigurationError, match="X_ACCESS_TOKEN_SECRET"):
        incomplete.validate_write()
