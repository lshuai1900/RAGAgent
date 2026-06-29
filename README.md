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
export QWEN_API_KEY=your-qwen-api-key        # LLM / Embedding API Key（必需）
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

# 编辑知识库（重命名 / 修改描述 / 修改状态，部分更新）
curl -X PATCH http://localhost:8000/api/v1/knowledge-bases/{kb_id} \
  -H "Content-Type: application/json" \
  -d '{"name":"new-kb-name","description":"updated description"}'

# 删除知识库（软删除：归档 + 尝试清理向量库 collection）
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id}
```

- `PATCH` 支持部分更新：仅传入的字段（`name` / `description` / `status`）会被修改；名称变更时会校验唯一性，重名返回 `code=10101`，知识库不存在返回 `404`（`code=10404`）。
- `DELETE` 为软删除：将知识库状态置为 `archived`，列表与详情接口不再返回；同时尝试删除对应 Milvus collection，删除失败仅记录日志、不回滚数据库。

### 文档摄取

```bash
# 上传文档（支持 txt/md/pdf）
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@doc.txt" \
  -F "kb_id={kb_id}"

# 查询文档状态（status: pending → completed/failed）
curl http://localhost:8000/api/v1/documents/{document_id}
```

### 知识库文件管理（重命名 / 删除 / 重新处理）

```bash
# 重命名文档（同一知识库内文件名唯一；重名返回 code=10301，文档不存在返回 404）
curl -X PATCH http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{document_id} \
  -H "Content-Type: application/json" \
  -d '{"filename":"新的文件名.md"}'

# 删除文档（同时删除对应向量索引 + 分块元数据 + 文档记录，递减知识库文档计数）
curl -X DELETE http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{document_id}

# 重新处理文档（删除旧向量与旧分块，复用已存储分块内容重新 embedding + 索引）
curl -X POST http://localhost:8000/api/v1/knowledge-bases/{kb_id}/documents/{document_id}/reprocess
```

- `PATCH` 重命名：文件名前后空格会被 trim，非空校验失败返回 422；同一知识库内重名返回 `code=10301`；文档不存在或不属于该知识库返回 `404`（`code=10304`）。
- `DELETE` 删除：必须同时删除 Milvus 向量索引（按 `document_id` 过滤），否则 RAG 检索仍会命中已删除文件内容；向量库删除失败为 best-effort（仅记录日志，不阻断 DB 删除）。
- `POST /reprocess` 重新处理：原始上传文件未持久化，因此复用 `t_document_chunk.content` 重新 embedding + 索引；若文档无分块内容（未完成分块阶段）返回 `code=10302` 并提示重新上传。

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

前端位于 `web/`，独立 `package.json`，技术栈：Vue 3 + Vite + TypeScript + Pinia + Ant Design Vue 4 + lucide-vue-next，所有用户可见文案为简体中文，整体采用 Yuxi 风格的知识库产品工作台视觉（蓝绿色主色 + 浅灰背景 + 白色面板 + 细边框）。

### 前端功能

当前前端已实现：

- 中文知识库产品工作台（左侧轻量导航 + 顶部标题区 + 主内容区，蓝绿色主题）
- 仪表盘健康检查（PostgreSQL / Milvus / 追踪编号 / 检查时间）
- 知识库列表（Yuxi 风格卡片网格 + 状态标签 + 文档数量 + 向量维度 + 创建时间 + 进入详情入口）
- 新建知识库（弹窗表单 + 校验，Embedding 模型与维度只读对齐后端）
- 知识库详情（沉浸式布局：隐藏左侧菜单 + 64px Header + 横向功能 Tab）
- 横向功能 Tab（文件管理 / 检索测试 / 聊天问答 三个真实功能；知识图谱 / 知识导图 / RAG 评估 / 评估基准 等暂缓项已隐藏，不在 UI 暴露入口）
- 文件管理（Yuxi 风格行列表：文件类型图标 + 文件名 + 状态徽标 + 细分隔线，非后台表格）
- 文档上传（拖拽上传 + TXT/Markdown/PDF + 50MB 校验 + 重复文件检测）
- 文档状态轮询（pending → parsing → chunking → embedding → indexing → completed/failed，每 3 秒轮询，全终态自动停止）
- 检索测试（复用 `POST /api/v1/chat/sse`，左右分栏展示回答与引用来源）
- 聊天问答（顶层 `/chat` 全局聊天页，顶部标题 + 右侧知识库选择器 + 左右分栏）
- POST SSE 流式输出（fetch + ReadableStream，禁用 EventSource）
- 引用来源展示（多条卡片 + 3 位小数相似度 + 内容摘要折叠 + 空状态"暂无引用来源"）
- API 地址设置（输入 + 测试连接 + 保存到 localStorage）
- 错误提示统一为中文 + 追踪编号

### 启动方式

后端：

```bash
make deps-up      # docker compose up -d（PostgreSQL + Milvus）
make sync         # uv sync
export QWEN_API_KEY=your-qwen-api-key
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

### 前端 UI 参考

本项目在轻量 RAG-only 范围内复制并改造了 Yuxi v0.7.0 的部分前端布局、组件、样式与交互实现，用于实现知识库、文档管理、检索测试、聊天问答、设置与健康检查等已实现功能的 UI 对齐。本项目不复制或启用 Yuxi 的 MCP、Skills、SubAgents、沙盒、LangGraph、多租户、权限、JWT、知识图谱、知识导图、RAG 评估、模型路由、Rerank 等重功能。第三方授权说明见 [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md)。

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

## 开源仓库说明

本仓库保留完整 MVP 源码、迁移、测试、配置模板和文档；不应提交本地运行数据、依赖安装目录、缓存、构建产物或真实密钥。使用 milvus-lite 时生成的 `milvus_lite.db/` 属于本地数据目录，请勿纳入版本管理。
