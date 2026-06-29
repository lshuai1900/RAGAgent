.PHONY: dev lint typecheck test test-unit test-integration migrate migrate-new sync deps-up deps-down format migrate-down

# Start local infrastructure: PostgreSQL + Milvus
deps-up:
	docker compose up -d

deps-down:
	docker compose down

# Install backend dependencies
sync:
	uv sync

# Start backend development server
dev:
	uv run uvicorn ragent.main:app --reload --host 0.0.0.0 --port 8000

# Lint and format check
lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests

# Type check
typecheck:
	uv run mypy src/ragent

# Tests
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

test-integration:
	uv run pytest tests/integration

# Database migrations
migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(msg)"

migrate-down:
	uv run alembic downgrade -1
