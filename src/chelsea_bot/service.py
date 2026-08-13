from __future__ import annotations

import logging

from chelsea_bot.config import Settings
from chelsea_bot.filtering import ChelseaMatcher
from chelsea_bot.models import RunResult
from chelsea_bot.state import StateStore
from chelsea_bot.x_api import XClient

LOGGER = logging.getLogger(__name__)


class BotService:
    def __init__(self, settings: Settings, client: XClient, state: StateStore) -> None:
        self.settings = settings
        self.client = client
        self.state = state
        self.matcher = ChelseaMatcher(settings.chelsea_terms)

    def _source_user_id(self, *, cache: bool = True) -> str:
        key = f"source_user_id:{self.settings.source_username.casefold()}"
        cached = self.state.get(key)
        if cache and cached:
            return cached
        resolved = self.client.user_id_by_username(self.settings.source_username)
        if cache:
            self.state.set(key, resolved)
        return resolved

    def _bot_user_id(self, *, cache: bool = True) -> str:
        cached = self.state.get("bot_user_id")
        if cache and cached:
            return cached
        resolved = self.client.authenticated_user_id()
        if cache:
            self.state.set("bot_user_id", resolved)
        return resolved

    def doctor(self) -> dict[str, str]:
        self.settings.validate_read()
        self.settings.validate_write()
        return {
            "source_username": self.settings.source_username,
            "source_user_id": self._source_user_id(cache=False),
            "bot_user_id": self._bot_user_id(cache=False),
            "result": "credentials and user lookups succeeded",
        }

    def run_once(self, *, live: bool) -> RunResult:
        self.settings.validate_read()
        if live:
            self.settings.validate_write()

        previous_checkpoint = self.state.last_seen_id
        source_user_id = self._source_user_id(cache=live)
        posts = sorted(
            self.client.posts_by_user(source_user_id, previous_checkpoint),
            key=lambda post: int(post.id),
        )
        if not posts:
            return RunResult(dry_run=not live, last_seen_id=previous_checkpoint)

        if previous_checkpoint is None and self.settings.bootstrap_mode == "baseline":
            newest = posts[-1].id
            if live:
                self.state.establish_baseline(newest)
                LOGGER.info(
                    "Baseline established at source post %s; no history was reposted", newest
                )
            else:
                LOGGER.info("Dry run would establish baseline at source post %s", newest)
            return RunResult(
                fetched=len(posts),
                bootstrapped=True,
                dry_run=not live,
                last_seen_id=newest if live else None,
            )

        matched = reposted = ignored = 0
        bot_user_id: str | None = None
        for post in posts:
            if live and self.state.was_processed(post.id):
                self.state.advance(post, matched=False, action="already_processed")
                continue

            is_match = self.matcher.matches(post.text)
            if is_match and live and reposted >= self.settings.max_reposts_per_run:
                LOGGER.warning(
                    "Per-run repost limit (%s) reached; remaining posts will be retried next run",
                    self.settings.max_reposts_per_run,
                )
                break

            if is_match:
                matched += 1
                if live:
                    bot_user_id = bot_user_id or self._bot_user_id()
                    self.client.repost(bot_user_id, post.id)
                    reposted += 1
                    self.state.advance(post, matched=True, action="reposted")
                    LOGGER.info("Reposted Chelsea source post %s", post.id)
                else:
                    LOGGER.info("Dry run matched source post %s", post.id)
            else:
                ignored += 1
                if live:
                    self.state.advance(post, matched=False, action="ignored")

        return RunResult(
            fetched=len(posts),
            matched=matched,
            reposted=reposted,
            ignored=ignored,
            dry_run=not live,
            last_seen_id=self.state.last_seen_id,
        )
