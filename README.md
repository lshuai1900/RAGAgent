# Ragent-Py

Ragent-Py 是一个基于 Python 技术栈实现的企业级 Agentic RAG MVP。项目参考
[nageoffer/ragent](https://github.com/nageoffer/ragent) 的架构思想，保留分层、抽象接口、流式问答、Trace ID 透传等工程实践，但不是 Java 代码的逐行翻译。

当前版本聚焦最小可运行闭环：

- 知识库管理
- TXT / Markdown / PDF 文档上传与摄取
- 文档解析、分块、Embedding、Milvus 向量入库
- 基于单知识库的向量检索
- OpenAI-compatible LLM 流式问答
- FastAPI SSE 接口
- Vue 3 前端控制台

## 技术栈

后端：

- Python 3.11+
- FastAPI + Uvicorn
- Pydantic v2
- SQLAlchemy 2.0 async + asyncpg + Alembic
- PostgreSQL 15
- Milvus Standalone
- OpenAI-compatible LLM / Embedding Client
- sse-starlette
- pytest / pytest-asyncio
- ruff / mypy
- uv

前端：

- Vue 3
- Vite
- TypeScript
- Pinia
- Vue Router
- Ant Design Vue
- lucide-vue-next

## 项目结构

```text
.
├── alembic/                  # 数据库迁移
├── configs/                  # 应用配置与 Prompt 模板
├── docs/
│   └── THIRD_PARTY_NOTICES.md
├── scripts/                  # 辅助脚本
├── src/ragent/
│   ├── api/                  # FastAPI 路由层
│   ├── schemas/              # Pydantic API Schema
│   ├── service/              # 业务编排
│   ├── domain/               # 纯领域对象
│   ├── persistence/          # ORM Model 与 Repository
│   ├── infra_ai/             # LLM / Embedding / Rerank 抽象与实现
│   ├── rag/                  # 检索、向量库、Prompt、Memory
│   ├── ingestion/            # 文档解析、分块、摄取 Pipeline
│   └── framework/            # 配置、DB、异常、SSE、Trace、Middleware
├── tests/                    # 单元测试与集成测试
└── web/                      # Vue 前端控制台
```

## 快速开始

### 1. 安装后端依赖

```bash
uv sync
```

### 2. 启动基础设施

```bash
docker compose up -d
```

该命令会启动 PostgreSQL 和 Milvus。

### 3. 配置环境变量

复制环境变量样例：

```bash
cp .env.example .env
```

至少需要配置：

```bash
QWEN_API_KEY=your-qwen-api-key
RAGENT__DB__URL=postgresql+asyncpg://ragent:ragent@localhost:5432/ragent
RAGENT__MILVUS__URI=http://localhost:19530
```

如果使用其他 OpenAI-compatible 服务，可同步调整 `QWEN_BASE_URL`、`LLM_MODEL`、`EMBEDDING_MODEL` 等变量。

### 4. 执行数据库迁移

```bash
uv run alembic upgrade head
```

或使用：

```bash
make migrate
```

### 5. 启动后端

```bash
make dev
```

后端默认地址：

```text
http://localhost:8000
```

健康检查：

```bash
curl http://localhost:8000/health
```

### 6. 启动前端

```bash
cd web
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

前端设置页可以修改后端 API 地址，默认使用 `http://localhost:8000`。

## 常用命令

```bash
make sync              # 安装后端依赖
make deps-up           # 启动 PostgreSQL + Milvus
make deps-down         # 停止基础设施
make migrate           # 执行 Alembic 迁移
make dev               # 启动 FastAPI 开发服务
make lint              # ruff check + format check
make format            # ruff format
make typecheck         # mypy
make test              # 全量测试
make test-unit         # 单元测试
make test-integration  # 集成测试
```

前端命令：

```bash
cd web
npm run dev
npm run build
npm run preview
npm run type-check
```

## API 示例

### 创建知识库

```bash
curl -X POST http://localhost:8000/api/v1/knowledge-bases \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品文档库",
    "description": "用于演示的知识库",
    "embedding_model": "text-embedding-v3",
    "embedding_dim": 1024,
    "chunk_strategy": "recursive",
    "chunk_size": 512,
    "chunk_overlap": 64
  }'
```

### 查询知识库列表

```bash
curl "http://localhost:8000/api/v1/knowledge-bases?page=1&page_size=20"
```

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "kb_id={kb_id}" \
  -F "file=@README.md"
```

支持的文件类型：

- `.txt`
- `.md`
- `.pdf`

### 查询文档状态

```bash
curl http://localhost:8000/api/v1/documents/{document_id}
```

文档状态流转：

```text
pending -> parsing -> chunking -> embedding -> indexing -> completed
                                                        -> failed
```

### 流式问答

```bash
curl -N -X POST http://localhost:8000/api/v1/chat/sse \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo-session-001",
    "kb_id": "{kb_id}",
    "question": "这份文档主要讲了什么？",
    "top_k": 5,
    "temperature": 0.0,
    "top_p": 1.0
  }'
```

SSE 事件类型：

```text
start  -> {"trace_id": "..."}
delta  -> {"content": "..."}
done   -> {"trace_id": "...", "finish_reason": "stop"}
error  -> {"trace_id": "...", "code": 30001, "message": "..."}
```

## 前端功能

当前前端提供一个轻量 RAG 控制台：

- 仪表盘与依赖健康检查
- 后端 API 地址配置
- 知识库列表、创建、编辑、删除
- 知识库详情页
- 文档上传、状态轮询、重命名、删除、重新处理
- 检索测试
- 聊天问答
- POST SSE 流式输出
- Trace ID 展示
- 引用来源展示

## 配置说明

主配置文件位于：

```text
configs/config.yaml
```

配置可通过环境变量覆盖。环境变量命名规则：

```text
RAGENT__{SECTION}__{KEY}
```

示例：

```bash
RAGENT__DB__URL=postgresql+asyncpg://ragent:ragent@localhost:5432/ragent
RAGENT__MILVUS__URI=http://localhost:19530
```

密钥不应写入配置文件或数据库明文，运行时从环境变量读取。

## 测试

单元测试不依赖真实 PostgreSQL、Milvus 或 LLM 服务：

```bash
make test-unit
```

集成测试需要先启动依赖：

```bash
make deps-up
make test-integration
```

完整检查：

```bash
make lint
make typecheck
make test
```

## MVP 暂不包含

当前开源版本不包含以下能力：

- MCP 工具集成
- 意图识别
- 查询改写
- 多路检索
- Rerank 模型调用
- 三态熔断器
- 队列式限流
- JWT 认证
- 复杂 Trace Span 树与可视化追踪
- Memory summarize 摘要压缩
- Celery / Dramatiq / Redis Queue
- 管理后台
- 对话标题生成
- PPT / HTML / unstructured 解析

## 开源发布注意事项

仓库应只保留源码、迁移、测试、配置模板、Prompt 模板、前端工程与必要文档。以下内容不应提交：

- `.env`
- `.venv/`
- `node_modules/`
- `web/dist/`
- `milvus_lite.db/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- 本地 IDE 配置
- 本地运行日志

第三方来源与授权说明见 [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)。

## License

本项目使用 MIT License，详见 [LICENSE](LICENSE)。
