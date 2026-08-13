from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from chelsea_bot.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    base = Settings(
        bearer_token="bearer",
        api_key="key",
        api_secret="secret",
        access_token="access",
        access_token_secret="access-secret",
        source_username="FabrizioRomano",
        chelsea_terms=("chelsea", "chelsea fc", "chelseafc", "@chelseafc", "#chelseafc"),
        state_path=tmp_path / "state.db",
        dry_run=True,
        bootstrap_mode="baseline",
        max_results=100,
        max_pages=5,
        max_reposts_per_run=5,
        request_timeout_seconds=20,
        log_level="INFO",
        api_base_url="https://api.x.test",
    )
    return replace(base)
