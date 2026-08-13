from __future__ import annotations

from dataclasses import replace

from chelsea_bot.config import Settings
from chelsea_bot.models import Post
from chelsea_bot.service import BotService
from chelsea_bot.state import StateStore


class FakeClient:
    def __init__(self, posts: list[Post]) -> None:
        self.posts = posts
        self.reposted: list[tuple[str, str]] = []
        self.source_lookups = 0
        self.bot_lookups = 0

    def user_id_by_username(self, username: str) -> str:
        assert username == "FabrizioRomano"
        self.source_lookups += 1
        return "source-123"

    def authenticated_user_id(self) -> str:
        self.bot_lookups += 1
        return "bot-456"

    def posts_by_user(self, user_id: str, since_id: str | None) -> list[Post]:
        assert user_id == "source-123"
        return self.posts

    def repost(self, bot_user_id: str, source_post_id: str) -> None:
        self.reposted.append((bot_user_id, source_post_id))


def test_first_live_run_establishes_baseline_without_reposts(settings: Settings) -> None:
    client = FakeClient([Post("10", "Chelsea update"), Post("12", "Chelsea again")])
    state = StateStore(settings.state_path)
    service = BotService(settings, client, state)  # type: ignore[arg-type]

    result = service.run_once(live=True)

    assert result.bootstrapped is True
    assert result.fetched == 2
    assert result.reposted == 0
    assert state.last_seen_id == "12"
    assert client.reposted == []
    assert client.bot_lookups == 0


def test_dry_run_never_advances_state_or_reposts(settings: Settings) -> None:
    client = FakeClient([Post("10", "Chelsea update")])
    state = StateStore(settings.state_path)
    service = BotService(settings, client, state)  # type: ignore[arg-type]

    result = service.run_once(live=False)

    assert result.bootstrapped is True
    assert result.dry_run is True
    assert state.last_seen_id is None
    assert state.get("source_user_id:fabrizioromano") is None
    assert client.reposted == []


def test_replay_reposts_only_matches_in_chronological_order(settings: Settings) -> None:
    settings = replace(settings, bootstrap_mode="replay")
    client = FakeClient(
        [
            Post("30", "Manchester United update"),
            Post("10", "CHELSEA have agreed terms"),
            Post("20", "Arsenal negotiations continue"),
        ]
    )
    state = StateStore(settings.state_path)
    service = BotService(settings, client, state)  # type: ignore[arg-type]

    result = service.run_once(live=True)

    assert result.matched == 1
    assert result.reposted == 1
    assert result.ignored == 2
    assert client.reposted == [("bot-456", "10")]
    assert state.last_seen_id == "30"


def test_repost_cap_leaves_unprocessed_posts_for_next_run(settings: Settings) -> None:
    settings = replace(settings, bootstrap_mode="replay", max_reposts_per_run=2)
    client = FakeClient([Post(str(post_id), "Chelsea") for post_id in (1, 2, 3)])
    state = StateStore(settings.state_path)
    service = BotService(settings, client, state)  # type: ignore[arg-type]

    result = service.run_once(live=True)

    assert result.reposted == 2
    assert state.last_seen_id == "2"
    assert [post_id for _, post_id in client.reposted] == ["1", "2"]


def test_doctor_forces_both_credential_paths(settings: Settings) -> None:
    client = FakeClient([])
    state = StateStore(settings.state_path)
    state.set("source_user_id:fabrizioromano", "old-source")
    state.set("bot_user_id", "old-bot")
    service = BotService(settings, client, state)  # type: ignore[arg-type]

    result = service.doctor()

    assert result["source_user_id"] == "source-123"
    assert result["bot_user_id"] == "bot-456"
    assert client.source_lookups == 1
    assert client.bot_lookups == 1
