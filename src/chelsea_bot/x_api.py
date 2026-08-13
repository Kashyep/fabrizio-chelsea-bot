from __future__ import annotations

from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from requests_oauthlib import OAuth1
from urllib3.util.retry import Retry

from chelsea_bot.config import Settings
from chelsea_bot.models import Post


class XAPIError(RuntimeError):
    """An X API request failed with a useful, secret-free message."""

    def __init__(self, operation: str, response: requests.Response) -> None:
        detail = ""
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("title") or str(payload.get("errors", ""))
        except (ValueError, AttributeError):
            detail = response.text[:300]
        reset = response.headers.get("x-rate-limit-reset")
        suffix = f" Rate-limit reset: {reset}." if response.status_code == 429 and reset else ""
        super().__init__(
            f"X API {operation} failed with HTTP {response.status_code}: "
            f"{detail or 'no detail'}.{suffix}"
        )
        self.status_code = response.status_code


class XClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            status=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
        )
        self.read_session = requests.Session()
        self.read_session.mount("https://", HTTPAdapter(max_retries=retry))
        self.read_session.headers.update(
            {
                "Authorization": f"Bearer {settings.bearer_token}",
                "User-Agent": "fabrizio-chelsea-bot/1.0",
            }
        )

    @property
    def timeout(self) -> int:
        return self.settings.request_timeout_seconds

    def _oauth(self) -> OAuth1:
        return OAuth1(
            self.settings.api_key,
            self.settings.api_secret,
            self.settings.access_token,
            self.settings.access_token_secret,
        )

    @staticmethod
    def _data(response: requests.Response, operation: str) -> Any:
        if not response.ok:
            raise XAPIError(operation, response)
        payload = response.json()
        if "data" not in payload:
            raise RuntimeError(f"X API {operation} returned no data")
        return payload["data"]

    def user_id_by_username(self, username: str) -> str:
        response = self.read_session.get(
            f"{self.settings.api_base_url}/2/users/by/username/{quote(username)}",
            timeout=self.timeout,
        )
        return str(self._data(response, f"lookup @{username}")["id"])

    def authenticated_user_id(self) -> str:
        response = requests.get(
            f"{self.settings.api_base_url}/2/users/me",
            auth=self._oauth(),
            headers={"User-Agent": "fabrizio-chelsea-bot/1.0"},
            timeout=self.timeout,
        )
        return str(self._data(response, "lookup authenticated user")["id"])

    def posts_by_user(self, user_id: str, since_id: str | None) -> list[Post]:
        posts: dict[str, Post] = {}
        pagination_token: str | None = None
        for _ in range(self.settings.max_pages):
            params: dict[str, str | int] = {
                "exclude": "retweets",
                "max_results": self.settings.max_results,
                "tweet.fields": "created_at",
            }
            if since_id:
                params["since_id"] = since_id
            if pagination_token:
                params["pagination_token"] = pagination_token

            response = self.read_session.get(
                f"{self.settings.api_base_url}/2/users/{quote(user_id)}/tweets",
                params=params,
                timeout=self.timeout,
            )
            if not response.ok:
                raise XAPIError("read source timeline", response)
            payload = response.json()
            for item in payload.get("data", []):
                post = Post(
                    id=str(item["id"]),
                    text=str(item["text"]),
                    created_at=item.get("created_at"),
                )
                posts[post.id] = post
            pagination_token = payload.get("meta", {}).get("next_token")
            if not pagination_token:
                break
        return list(posts.values())

    def repost(self, bot_user_id: str, source_post_id: str) -> None:
        response = requests.post(
            f"{self.settings.api_base_url}/2/users/{quote(bot_user_id)}/retweets",
            json={"tweet_id": source_post_id},
            auth=self._oauth(),
            headers={"User-Agent": "fabrizio-chelsea-bot/1.0"},
            timeout=self.timeout,
        )
        data = self._data(response, f"repost {source_post_id}")
        if data.get("retweeted") is not True:
            raise RuntimeError(f"X API did not confirm repost {source_post_id}")
