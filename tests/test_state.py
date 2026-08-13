from __future__ import annotations

from pathlib import Path

import pytest

from chelsea_bot.models import Post
from chelsea_bot.state import StateStore


def test_state_records_a_hash_not_source_text(tmp_path: Path) -> None:
    state = StateStore(tmp_path / "state.db")
    post = Post(id="10", text="Chelsea private-ish sample", created_at="2026-01-01T00:00:00Z")
    state.advance(post, matched=True, action="reposted")

    summary = state.summary()
    assert summary["last_seen_id"] == "10"
    assert summary["observed"] == 1
    assert summary["matched"] == 1
    assert summary["reposted"] == 1

    import sqlite3

    with sqlite3.connect(state.path) as connection:
        stored = connection.execute("SELECT text_sha256 FROM events").fetchone()[0]
    assert stored != post.text
    assert len(stored) == 64


def test_checkpoint_cannot_move_backwards(tmp_path: Path) -> None:
    state = StateStore(tmp_path / "state.db")
    state.advance(Post("20", "Chelsea"), matched=True, action="reposted")
    with pytest.raises(ValueError, match="backwards"):
        state.advance(Post("19", "Arsenal"), matched=False, action="ignored")
