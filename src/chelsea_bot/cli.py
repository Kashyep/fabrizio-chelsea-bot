from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

from requests import RequestException

from chelsea_bot.config import ConfigurationError, Settings
from chelsea_bot.locking import AlreadyRunningError, ProcessLock
from chelsea_bot.service import BotService
from chelsea_bot.state import StateStore
from chelsea_bot.x_api import XAPIError, XClient


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chelsea-bot",
        description="Repost only Fabrizio Romano posts that mention Chelsea.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("run", "Run one polling cycle and exit."),
        ("daemon", "Poll continuously at a fixed interval."),
    ):
        command = subparsers.add_parser(name, help=help_text)
        mode = command.add_mutually_exclusive_group()
        mode.add_argument("--live", action="store_true", help="Enable real reposts.")
        mode.add_argument("--dry-run", action="store_true", help="Never repost or advance state.")
        command.add_argument(
            "--bootstrap-history",
            action="store_true",
            help="On an empty state database, process recent history instead of baselining.",
        )
        if name == "daemon":
            command.add_argument("--interval", type=int, default=300, help="Seconds between polls.")

    subparsers.add_parser("doctor", help="Validate all credentials without creating a repost.")
    subparsers.add_parser("status", help="Show the local checkpoint and audit counts.")
    return parser


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def _live_mode(args: argparse.Namespace, settings: Settings) -> bool:
    if args.live:
        return True
    if args.dry_run:
        return False
    return not settings.dry_run


def _service(settings: Settings) -> BotService:
    state = StateStore(settings.state_path)
    return BotService(settings, XClient(settings), state)


def _run_cycle(settings: Settings, *, live: bool) -> int:
    lock_path = Path(f"{settings.state_path}.lock")
    with ProcessLock(lock_path):
        result = _service(settings).run_once(live=live)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = Settings.from_env()
        _configure_logging(settings.log_level)

        if args.command == "status":
            print(json.dumps(StateStore(settings.state_path).summary(), indent=2, sort_keys=True))
            return 0

        if args.command == "doctor":
            lock_path = Path(f"{settings.state_path}.lock")
            with ProcessLock(lock_path):
                result = _service(settings).doctor()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.bootstrap_history:
            settings = replace(settings, bootstrap_mode="replay")
        live = _live_mode(args, settings)

        if args.command == "run":
            return _run_cycle(settings, live=live)

        if args.interval < 60:
            raise ConfigurationError("Daemon interval must be at least 60 seconds")
        while True:
            try:
                _run_cycle(settings, live=live)
            except (XAPIError, RequestException) as exc:
                logging.getLogger(__name__).error("Polling cycle failed: %s", exc)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 130
    except (
        ConfigurationError,
        XAPIError,
        RequestException,
        AlreadyRunningError,
        OSError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
