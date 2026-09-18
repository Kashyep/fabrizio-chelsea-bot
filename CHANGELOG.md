# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-13

### Added
- Initial release: Chelsea-only Fabrizio Romano repost bot
- X API v2 integration with OAuth 1.0a user context
- Native repost endpoint (preserves attribution and media)
- SQLite checkpoint + audit trail with SHA-256 text hashes
- Case-insensitive word-boundary Chelsea term matching
- Safe defaults: dry-run mode, baseline on first live run
- Per-run repost cap (default 5) to prevent bursts
- Process lock to prevent overlapping runs
- GitHub Actions workflow (scheduled, gated by BOT_ENABLED)
- Docker Compose deployment with named volume
- Comprehensive setup guide (PDF + Markdown)
- Full test suite with fake X clients (no live API calls)

### Security
- Credentials via environment variables only
- No secrets in logs, cache, or database
- Read-only GitHub Actions permissions
- Unprivileged Docker user (UID 10001)