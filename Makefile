.PHONY: dev lint typecheck test test-unit test-integration migrate migrate-new sync deps-up

# 启动依赖（PostgreSQL + Milvus）
deps-up:
	docker compose up -d

deps-down:
	docker compose down

# 安装依赖
sync:
	uv sync

# 启动开发服务
dev:
	uv run uvicorn ragent.main:app --reload --host 0.0.0.0 --port 8000

# Lint
lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

format:
	uv run ruff format src tests

# Type check
typecheck:
	uv run mypy src/ragent

# 测试
test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

test-integration:
	uv run pytest tests/integration

# 数据库迁移
migrate:
	uv run alembic upgrade head

migrate-new:
	uv run alembic revision --autogenerate -m "$(msg)"

migrate-down:
	uv run alembic downgrade -1
