# Ragent-Py

基于 [nageoffer/ragent](https://github.com/nageoffer/ragent) 架构思想的 **Python 复刻版** 企业级 Agentic RAG 平台。

技术栈：Python 3.11+ / FastAPI / SQLAlchemy 2.0 async / PostgreSQL / Milvus / OpenAI-compatible LLM。

## 快速开始

### 1. 启动依赖

```bash
make deps-up   # docker compose up -d（PostgreSQL + Milvus）
```

### 2. 安装依赖

```bash
make sync      # uv sync
```

### 3. 数据库迁移

```bash
make migrate   # alembic upgrade head
```

### 4. 启动服务

```bash
make dev       # uvicorn ragent.main:app --reload
```

服务默认监听 `http://localhost:8000`，访问 `GET /health` 查看依赖连通性。

## 开发命令

| 命令 | 说明 |
|---|---|
| `make lint` | ruff 检查 + 格式校验 |
| `make format` | ruff 自动格式化 |
| `make typecheck` | mypy 类型检查 |
| `make test` | 全部测试 |
| `make test-unit` | 单元测试 |
| `make test-integration` | 集成测试 |
| `make migrate-new msg="xxx"` | 生成新迁移 |

## 项目结构

```
src/ragent/
├── api/            # FastAPI 路由层（只调 service）
├── schemas/        # Pydantic v2 API Schema（顶层独立）
├── service/        # 业务编排中心
├── domain/         # 纯领域（enums / dto / value_objects）
├── persistence/    # ORM Model + Repository
├── infra_ai/       # LLM / Embedding / Rerank 客户端
├── rag/            # 检索 / 向量库 / Prompt / Memory
├── ingestion/      # 文档解析 / 分块 / Pipeline
└── framework/      # 通用基础设施（config / db / trace / middleware）
```

详细设计见 `docs/`，规则约束见 `.trae/rules/`，协作指引见 `AGENTS.md`。
