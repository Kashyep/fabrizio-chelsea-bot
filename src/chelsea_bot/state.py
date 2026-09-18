from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from chelsea_bot.models import Post


class StateStore:
    """Durable checkpoint and audit trail backed by SQLite."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=DELETE;
                PRAGMA synchronous=FULL;
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    source_post_id TEXT PRIMARY KEY,
                    observed_at TEXT NOT NULL,
                    source_created_at TEXT,
                    text_sha256 TEXT NOT NULL,
                    matched INTEGER NOT NULL,
                    action TEXT NOT NULL
                );
                """
            )

    def get(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else None

    def set(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO metadata(key, value) VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    @property
    def last_seen_id(self) -> str | None:
        return self.get("last_seen_id")

    def advance(self, post: Post, *, matched: bool, action: str) -> None:
        current = self.last_seen_id
        if current is not None and int(post.id) < int(current):
            raise ValueError("Cannot move the source-post checkpoint backwards")
        digest = hashlib.sha256(post.text.encode("utf-8")).hexdigest()
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events(
                    source_post_id, observed_at, source_created_at, text_sha256, matched, action
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_post_id) DO NOTHING
                """,
                (post.id, now, post.created_at, digest, int(matched), action),
            )
            connection.execute(
                """
                INSERT INTO metadata(key, value) VALUES('last_seen_id', ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (post.id,),
            )

    def establish_baseline(self, newest_post_id: str) -> None:
        self.set("last_seen_id", newest_post_id)
        self.set("baseline_established_at", datetime.now(UTC).isoformat())

    def was_processed(self, source_post_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM events WHERE source_post_id = ?", (source_post_id,)
            ).fetchone()
        return row is not None

    def summary(self) -> dict[str, str | int | None]:
        with self._connect() as connection:
            counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS observed,
                    COALESCE(SUM(matched), 0) AS matched,
                    COALESCE(SUM(action = 'reposted'), 0) AS reposted
                FROM events
                """
            ).fetchone()
        return {
            "state_path": str(self.path.resolve()),
            "last_seen_id": self.last_seen_id,
            "observed": int(counts["observed"]),
            "matched": int(counts["matched"]),
            "reposted": int(counts["reposted"]),
        }
