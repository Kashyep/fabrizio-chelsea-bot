# Contributing

## Development setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pre-commit install
```

## Running checks

```bash
ruff check .
pytest --cov=chelsea_bot --cov-report=term-missing
```

## Pull requests

- Add tests for new behavior first
- Keep changes focused and minimal
- Update documentation if user-facing behavior changes
- Never test write behavior against a personal X account; use a dedicated test account
- Ensure `ruff check .` and `pytest` pass before requesting review

## Code style

- Follow existing patterns in `src/chelsea_bot/`
- Type hints required for public functions
- Docstrings for public classes/functions
- No comments unless explaining *why*, not *what*
- Line length: 100 (enforced by ruff)

## Security

- Never commit `.env`, credentials, or `data/state.db`
- Report vulnerabilities via private GitHub security advisory
- Rotate credentials immediately if exposed