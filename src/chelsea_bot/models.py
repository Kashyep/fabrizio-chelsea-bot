from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Post:
    """The source-post fields needed by the bot."""

    id: str
    text: str
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class RunResult:
    """Machine-readable summary returned after one polling cycle."""

    fetched: int = 0
    matched: int = 0
    reposted: int = 0
    ignored: int = 0
    bootstrapped: bool = False
    dry_run: bool = True
    last_seen_id: str | None = None
