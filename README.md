# Ragent-Py

基于 [nageoffer/ragent](https://github.com/nageoffer/ragent) 架构思想的 **Python 复刻版** 企业级 Agentic RAG 平台。

技术栈：Python 3.11+ / FastAPI / SQLAlchemy 2.0 async / PostgreSQL / Milvus / OpenAI-compatible LLM。

## 快速开始

### 1. 启动依赖

```bash
make deps-up   # docker compose up -d（PostgreSQL + Milvus）
```

无 Docker 环境时可使用本地 PostgreSQL + milvus-lite：

```bash
# PostgreSQL：apt 安装并启动后创建库
sudo apt-get install -y postgresql postgresql-contrib
sudo pg_ctlcluster 16 main start
sudo -u postgres createuser ragent --createdb --login --password
sudo -u postgres psql -c "ALTER USER ragent PASSWORD 'ragent';"
sudo -u postgres createdb -O ragent ragent

# Milvus-lite（pip 包，无需 Docker）
uv pip install milvus-lite
export RAGENT__MILVUS__URI=./milvus_lite.db
```

### 2. 安装依赖

```bash
make sync      # uv sync
```

### 3. 配置环境变量

```bash
export QWEN_API_KEY=sk-xxx        # LLM / Embedding API Key（必需）
export RAGENT__MILVUS__URI=http://localhost:19530   # 或 ./milvus_lite.db
```

### 4. 数据库迁移

```bash
make migrate   # alembic upgrade head
```

### 5. 启动服务

```bash
make dev       # uvicorn ragent.main:app --reload
```

服务默认监听 `http://localhost:8000`，访问 `GET /health` 查看依赖连通性。

## API 接口示例

### 健康检查

```bash
curl http://localhost:8000/health
```

### 知识库管理

```bash
# 创建知识库
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{"name":"my-kb","embedding_dim":1024}'

# 列出知识库
curl "http://localhost:8000/api/v1/knowledge-bases?page=1&page_size=10"

# 查询知识库
curl http://localhost:8000/api/v1/knowledge-bases/{kb_id}
```

### 文档摄取

```bash
# 上传文档（支持 txt/md/pdf）
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@doc.txt" \
  -F "kb_id={kb_id}"

# 查询文档状态（status: pending → completed/failed）
curl http://localhost:8000/api/v1/documents/{document_id}
```

### 流式问答（SSE）

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/sse \
  -H "Content-Type: application/json" \
  -d '{"session_id":"sess-001","kb_id":"{kb_id}","question":"你的问题"}'
```

SSE 事件流：

```
event: start
data: {"trace_id": "xxx"}

event: delta
data: {"content": "回答片段"}

event: done
data: {"trace_id": "xxx", "finish_reason": "stop"}
```

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

## 验收命令

```bash
make lint           # ruff check + ruff format --check
make typecheck      # mypy src/ragent
make test           # pytest 全部
uv run pytest tests/unit -v          # 单元测试（无外部依赖）
uv run pytest tests/integration -v   # 集成测试（需 PG + Milvus）
```

集成测试无 QWEN_API_KEY 时使用 Mock Embedding/LLM，无需真实 API 调用。

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
