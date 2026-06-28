# PROJECT_SPEC.md

> Ragent-Py 项目规格说明书

---

## 1. 项目背景

Ragent-Py 是基于 [nageoffer/ragent](https://github.com/nageoffer/ragent) 架构思想的 Python 复刻版企业级 Agentic RAG 平台。

原项目 ragent 是一个 Java/Spring Boot 3.5.7 实现的企业级 Agentic RAG 系统，覆盖从文档入库到智能问答的完整链路：多路检索、树形意图识别、模型路由与容错、MCP 集成、链路追踪等生产级特性。后端约 40000 行 Java 代码、400+ 源文件、20 张业务表。

本项目旨在用 Python 技术栈复刻其架构思想与工程实践，构建一个可落地、可扩展、可面试讲解的企业级 Agentic RAG 平台。

---

## 2. 与 nageoffer/ragent 的关系

| 维度 | 原项目（ragent） | 本项目（ragent-py） |
|---|---|---|
| 语言 | Java 17 | Python 3.11+ |
| Web 框架 | Spring Boot 3.5.7 | FastAPI + Uvicorn |
| ORM | MyBatis-Plus 3.5.14 | SQLAlchemy 2.0 async |
| 业务库 | MySQL | PostgreSQL 15 |
| 向量库 | Milvus 2.6.6 / pgvector | Milvus Standalone |
| LLM | 自实现 ChatClient | OpenAI-compatible Client（手搓抽象） |
| 依赖注入 | Spring DI | FastAPI Depends |
| 异步 | 线程池 + TtlExecutors | asyncio + contextvars |
| 多模块 | Maven 4 模块 | Python src-layout 单包多子包 |
| 认证 | Sa-Token | JWT（MVP 暂缓） |
| 消息队列 | RocketMQ | FastAPI BackgroundTasks（MVP） |
| 文档解析 | Apache Tika | pypdf + python-docx + 自实现 |

**关系定位**：复刻架构思想与工程实践，不是 Java 代码逐行翻译。

---

## 3. Python 复刻原则

1. **复刻架构思想，不复刻语言特性**：对标原项目分层（framework / infra-ai / bootstrap）、扩展点（Strategy/Registry/Chain）、StreamChatPipeline 8 阶段、三态熔断、队列限流等工程思想。
2. **不复刻 Java 特有机制**：Spring DI → FastAPI 依赖注入；MyBatis-Plus → SQLAlchemy 2.0 async；Sa-Token → JWT；TtlExecutors → contextvars + asyncio；Maven 多模块 → Python src-layout。
3. **保留工程深度**：手搓 LLM/Embedding/VectorStore/Retriever 等抽象层，保留工程可控性，不直接套壳 LangChain/LlamaIndex。
4. **技术栈对齐原项目选型**：Milvus（与原项目一致）、PostgreSQL、qwen-plus / OpenAI 兼容 LLM。
5. **MVP 收敛**：第一阶段只做单知识库 + 单轮向量检索 + LLM 流式 SSE，砍掉复杂特性。

---

## 4. MVP 目标

构建一个最小可运行的企业级 Agentic RAG MVP，完成以下闭环：

```
上传文档（TXT/MD/PDF）
  → 文档解析
  → 分块
  → Embedding
  → Milvus 入库 + PostgreSQL 元数据落库

单轮问答
  → 问题向量化
  → Milvus top-K 检索
  → Prompt 拼装
  → LLM 流式 SSE 输出
```

### MVP 必须具备
- 知识库 CRUD（单知识库）
- 文档上传 → 解析 → 分块 → Embedding → 入库（异步 BackgroundTasks）
- 单轮问答：向量检索 + Prompt 拼装 + LLM 流式 SSE
- 统一响应体 + 全局异常拦截
- trace_id 透传 + X-Trace-Id 响应头 + 结构化日志
- 可 Mock 的 LLM/Embedding 客户端

---

## 5. 非目标（MVP 不做）

以下功能在 MVP 三批任务中**不实现**，留待后续阶段：

- 意图识别（树形分类 / IntentResolver）
- 多路检索（IntentDirected / VectorGlobal 多通道并行）
- 查询改写（QueryRewrite）
- MCP 工具集成
- 对话记忆摘要压缩（Memory summarize）
- 三态熔断器 + 模型路由降级
- 队列式限流
- JWT 认证
- 复杂 Trace Span 树 / `@rag_trace_node` / 可视化追踪
- PPT / HTML / unstructured 解析
- Rerank 模型（非 Identity）
- Celery / Dramatiq / Redis Queue 任务队列
- 管理后台 API（除 KB / 文档 CRUD 外）
- 对话标题生成
- 多知识库路由

---

## 6. 技术栈

| 类别 | 选型 | 说明 |
|---|---|---|
| 语言 | Python 3.11+ | match 语句、TaskGroup、ExceptionGroup |
| Web | FastAPI + Uvicorn | 原生 async + StreamingResponse SSE |
| 数据校验 | Pydantic v2 | API Schema、配置、领域 DTO |
| ORM | SQLAlchemy 2.0 async + asyncpg + Alembic | DB Model 与 API Schema 分层 |
| 业务库 | PostgreSQL 15 | 知识库/文档/分块/会话/消息/Trace |
| 向量库 | Milvus Standalone 2.x | 与原项目技术路线一致；通过 BaseVectorStore 抽象，后续可切 pgvector/Qdrant |
| LLM | OpenAI-compatible LLM Client（httpx async） | 默认 qwen-plus / DashScope 兼容端点 |
| Embedding | OpenAI-compatible Embedding Client | 同上 |
| 文档解析 | pypdf + python-docx + 自实现 | PDF/Word（MVP 仅 TXT/MD/PDF） |
| 分块 | 自实现 BaseChunker | 固定/段落/递归 |
| SSE | sse-starlette | 事件流封装 |
| 配置 | pydantic-settings + YAML | 类型安全配置 |
| 异步任务 | FastAPI BackgroundTasks | MVP 锁定，不引入 Celery |
| 测试 | pytest + pytest-asyncio | 单元/集成分层 |
| Lint/Type | ruff + mypy | 静态检查 |
| 依赖管理 | uv | 锁文件 + 快速安装 |

---

## 7. 三批交付范围

### 第 0 步：文档与规则落地（已完成）
- AGENTS.md
- docs/（7 份设计文档）
- .trae/rules/（16 份规则文件）
- 不写任何业务代码

### 第一批：T1-T4 项目骨架与基础设施
- T1：项目骨架与依赖（uv、ruff、mypy、docker-compose、空包结构）
- T2：配置与基础设施（pydantic-settings、async engine、trace_id 中间件、结构化日志）
- T3：持久化模型与迁移（7 张表 SQLAlchemy Model + Alembic + BaseRepository）
- T4：异常、统一响应与 health（三级异常、ApiResponse、/health 接口）

**交付物**：可启动的空 FastAPI 应用 + /health + 数据库 schema（含 TraceSpan 预留表）+ 异常响应体系 + trace_id 透传。

### 第二批：T5-T9 文档摄取链路
- T5：文档解析（TXT/MD/PDF）
- T6：分块器（Recursive/Sentence/Fixed）
- T7：Embedding 客户端（OpenAI-compatible）
- T8：Milvus 向量库（BaseVectorStore + Milvus 实现）
- T9：摄取 Pipeline + 文档/KB API（BackgroundTasks 触发）

**交付物**：可上传 TXT/MD/PDF → 异步分块入库 → Milvus 可检索 + PG 有元数据。

### 第三批：T10-T12、T14-T15、T18 检索与流式问答端到端
- T10：检索器与后处理（VectorRetriever + DedupPostProcessor + IdentityReranker）
- T11：LLM 客户端（OpenAI-compatible + SSE 流式 + 首包探测）
- T12：Prompt 模板服务
- T14：Chat Service 编排（load_history → retrieve → prompt → stream_chat）
- T15：SSE 流式接口（/api/v1/chat/sse）
- T18：端到端测试

**交付物**：完整 MVP 闭环——上传文档 → 单轮流式问答（向量检索 + LLM SSE）。

### 当前开源状态
- MVP 后端、前端、迁移、测试与文档均保留。
- 本地运行数据、缓存、依赖安装目录与构建产物不纳入开源仓库。
- 暂缓项仍不属于当前公开版本范围。

---

## 8. 验收基线

详细验收标准见 [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)。
