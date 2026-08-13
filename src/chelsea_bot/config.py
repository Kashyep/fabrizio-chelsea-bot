from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    """Raised when environment configuration is missing or unsafe."""


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false, not {value!r}")


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _secret(name: str) -> str | None:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else None


@dataclass(frozen=True, slots=True)
class Settings:
    bearer_token: str | None
    api_key: str | None
    api_secret: str | None
    access_token: str | None
    access_token_secret: str | None
    source_username: str
    chelsea_terms: tuple[str, ...]
    state_path: Path
    dry_run: bool
    bootstrap_mode: str
    max_results: int
    max_pages: int
    max_reposts_per_run: int
    request_timeout_seconds: int
    log_level: str
    api_base_url: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        terms = tuple(
            term.strip()
            for term in os.getenv(
                "CHELSEA_TERMS", "chelsea,chelsea fc,chelseafc,@chelseafc,#chelseafc"
            ).split(",")
            if term.strip()
        )
        if not terms:
            raise ConfigurationError("CHELSEA_TERMS must contain at least one term")

        bootstrap_mode = os.getenv("BOOTSTRAP_MODE", "baseline").strip().lower()
        if bootstrap_mode not in {"baseline", "replay"}:
            raise ConfigurationError("BOOTSTRAP_MODE must be 'baseline' or 'replay'")

        source_username = os.getenv("SOURCE_USERNAME", "FabrizioRomano").strip().lstrip("@")
        if not source_username:
            raise ConfigurationError("SOURCE_USERNAME cannot be empty")

        return cls(
            bearer_token=_secret("X_BEARER_TOKEN"),
            api_key=_secret("X_API_KEY"),
            api_secret=_secret("X_API_SECRET"),
            access_token=_secret("X_ACCESS_TOKEN"),
            access_token_secret=_secret("X_ACCESS_TOKEN_SECRET"),
            source_username=source_username,
            chelsea_terms=terms,
            state_path=Path(os.getenv("STATE_PATH", "data/state.db")).expanduser(),
            dry_run=_bool_env("DRY_RUN", True),
            bootstrap_mode=bootstrap_mode,
            max_results=_int_env("MAX_RESULTS", 100, 5, 100),
            max_pages=_int_env("MAX_PAGES", 5, 1, 20),
            max_reposts_per_run=_int_env("MAX_REPOSTS_PER_RUN", 5, 1, 25),
            request_timeout_seconds=_int_env("REQUEST_TIMEOUT_SECONDS", 20, 5, 120),
            log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
            api_base_url=os.getenv("X_API_BASE_URL", "https://api.x.com").strip().rstrip("/"),
        )

    def validate_read(self) -> None:
        if not self.bearer_token:
            raise ConfigurationError("X_BEARER_TOKEN is required to read public posts")

    def validate_write(self) -> None:
        missing = [
            name
            for name, value in (
                ("X_API_KEY", self.api_key),
                ("X_API_SECRET", self.api_secret),
                ("X_ACCESS_TOKEN", self.access_token),
                ("X_ACCESS_TOKEN_SECRET", self.access_token_secret),
            )
            if not value
        ]
        if missing:
            raise ConfigurationError(
                "Live mode requires these OAuth 1.0a credentials: " + ", ".join(missing)
            )
