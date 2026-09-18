.PHONY: install test lint fmt check build clean run-doctor run-dry-run status

install:
	python -m pip install -e ".[dev]"
	pre-commit install

test:
	pytest --cov=chelsea_bot --cov-report=term-missing

lint:
	ruff check .

fmt:
	ruff format .
	ruff check . --fix

check: lint test

build:
	python -m pip wheel . -w dist

clean:
	rm -rf dist build *.egg-info .pytest_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-doctor:
	chelsea-bot doctor

run-dry-run:
	chelsea-bot run --dry-run

status:
	chelsea-bot status

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-logs:
	docker compose logs -f bot

docker-down:
	docker compose down

docker-status:
	docker compose exec bot chelsea-bot status