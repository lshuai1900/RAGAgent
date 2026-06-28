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

## 前端

前端位于 `web/`，独立 `package.json`，技术栈：Vue 3 + Vite + TypeScript + Pinia + Ant Design Vue 4 + lucide-vue-next，所有用户可见文案为简体中文（工程控制台风格）。

### 前端功能

当前前端已实现：

- 中文工程控制台（左侧菜单 + 顶部标题 + 主内容区）
- 仪表盘健康检查（PostgreSQL / Milvus / 追踪编号 / 检查时间）
- 知识库列表（卡片网格 + 状态标签 + 文档数量 + 创建时间）
- 新建知识库（弹窗表单 + 校验，Embedding 模型与维度只读对齐后端）
- 知识库详情（基本信息 + 标签页：文件管理 / 检索测试 / 聊天问答 / 配置）
- 文档上传（拖拽上传 + TXT/Markdown/PDF + 50MB 校验 + 重复文件检测）
- 文档状态轮询（pending → parsing → chunking → embedding → indexing → completed/failed，每 3 秒轮询，全终态自动停止）
- 检索测试（复用 `POST /api/v1/chat/sse`，左右分栏展示回答与引用来源）
- 聊天问答（知识库详情页标签页 + 顶层 `/chat` 全局聊天页）
- POST SSE 流式输出（fetch + ReadableStream，禁用 EventSource）
- 引用来源展示（多条卡片 + 3 位小数相似度 + 内容摘要折叠 + 空状态"暂无引用来源"）
- API 地址设置（输入 + 测试连接 + 保存到 localStorage）
- 错误提示统一为中文 + 追踪编号

### 启动方式

后端：

```bash
make deps-up      # docker compose up -d（PostgreSQL + Milvus）
make sync         # uv sync
export QWEN_API_KEY=sk-xxx
make migrate      # alembic upgrade head
make dev          # uvicorn ragent.main:app --reload
```

前端：

```bash
cd web
npm install
npm run dev
```

访问：

```text
前端：http://localhost:5173
后端 API：http://localhost:8000
```

后端已配置 CORS 允许 `http://localhost:5173` 与 `http://127.0.0.1:5173`，前端开发期无需额外代理。

### 演示流程

1. 启动后端与前端（见上方"启动方式"）。
2. 浏览器打开 `http://localhost:5173`，进入「仪表盘」确认 PostgreSQL 与 Milvus 状态为"正常"。
3. 进入「知识库」，点击「新建知识库」，填写名称后创建。
4. 点击知识库卡片进入详情页。
5. 在「文件管理」标签页点击「上传文档」，选择 TXT/Markdown/PDF 文件上传。
6. 等待文档状态从"待处理"流转到"已完成"（页面每 3 秒自动刷新）。
7. 切换到「检索测试」标签页，输入查询内容，点击「开始检索」，查看流式回答与右侧引用来源。
8. 切换到「聊天问答」标签页，输入问题，点击「发送」，查看流式回答与追踪编号。
9. 或进入左侧菜单「聊天问答」，选择知识库后发起全局问答。
10. 回答区域的「追踪编号」可用于问题定位反馈给后端。

### 注意事项

- 前端不会保存 API Key / 数据库密码 / 模型密钥。
- 前端只调用 FastAPI 后端（`/health`、`/api/v1/*`），不直接访问 PostgreSQL、Milvus、Embedding API、LLM API。
- 后端 SSE 是 POST 接口（`POST /api/v1/chat/sse`），因此前端使用 `fetch + ReadableStream` 解析事件流，不使用 `EventSource`（EventSource 仅支持 GET）。
- API Base URL 保存在 localStorage（key：`ragent.apiBaseUrl`），默认 `http://localhost:8000`，可在「设置」页修改并测试连接。
- 后端 `done` 事件可能不携带引用来源，此时前端显示"暂无引用来源"，不伪造数据。

### 未实现功能

前端 MVP 未实现以下功能（暂缓项）：

- MCP 工具集成
- 意图识别 / 查询改写 / 多路检索
- Rerank 模型配置界面
- 三态熔断 / 限流 / 模型路由降级
- JWT / 登录认证 / 用户权限 / 多租户
- 知识图谱 / RAG 评估 / 对话标题自动生成
- 会话列表 / 历史会话管理 / 多轮复杂会话切换
- 管理后台（除知识库 / 文档 CRUD 外）
- 文档删除 / 重新摄取 / 知识库编辑删除（后端无接口）
- 暗色主题 / 国际化（i18n）/ 移动端适配

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
