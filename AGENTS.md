# AGENTS.md

> 本文件是 Ragent-Py 项目的 AI 协作强约束指引。任何 AI 助手（含 Trae）在修改本项目代码前必须先完整阅读本文件、`docs/` 与 `.trae/rules/`。

---

## 1. 项目定位

Ragent-Py 是基于 [nageoffer/ragent](https://github.com/nageoffer/ragent) 架构思想的 **Python 复刻版** 企业级 Agentic RAG 平台。

- **原项目**：Java 17 + Spring Boot 3.5.7 + MyBatis-Plus + Milvus，4 个 Maven 模块（framework / infra-ai / mcp-server / bootstrap）。
- **本项目**：Python 3.11+ + FastAPI + SQLAlchemy 2.0 async + Milvus，src-layout 单包多子包，保留分层边界。
- **复刻原则**：复刻架构思想与工程实践（分层、扩展点、StreamChatPipeline、Trace、熔断、限流），**不是 Java 逐行翻译**，不照搬 Spring 特有机制（Spring DI / Sa-Token / TtlExecutors / Maven 多模块等）。
- **MVP 取舍**：第一阶段只做单知识库 + 单轮向量检索 + LLM 流式 SSE，砍掉意图/MCP/记忆摘要/多路检索/Rerank 模型/熔断/限流/JWT/管理后台/复杂 Trace。

---

## 2. 当前阶段

**当前阶段：完整 MVP 代码版 — 开源整理与验收。**

本仓库已完成 MVP 三批代码实现：项目骨架与基础设施、文档摄取链路、检索与流式问答端到端。当前开源整理阶段只做发布前清理、文档对齐、验收检查与必要的安全卫生处理；不新增超出 MVP 的业务功能。

## 3. 后续阶段

| 阶段 | 范围 | 内容 |
|---|---|---|
| 第一批 | T1-T4 | 项目骨架与基础设施：依赖、配置、数据库模型、迁移、异常响应、health 接口 |
| 第二批 | T5-T9 | 文档摄取链路：文档解析（TXT/MD/PDF）、分块、Embedding、Milvus、摄取 Pipeline（BackgroundTasks） |
| 第三批 | T10-T12、T14-T15、T18 | 检索与流式问答端到端：检索器、后处理、LLM 客户端、Prompt 模板、Chat Service 编排、SSE 流式接口、端到端测试 |

**严格三批推进纪律**：MVP 三批已完成。后续开发仍需按阶段推进，每批完成后通过验收检查再启动下一批；禁止在未确认新阶段目标前一次性铺开后续功能。

---

## 4. 技术栈（锁定，不得擅自更换）

| 类别 | 选型 |
|---|---|
| 语言 | Python 3.11+ |
| Web | FastAPI + Uvicorn |
| 数据校验 | Pydantic v2 |
| ORM | SQLAlchemy 2.0 async + asyncpg + Alembic |
| 业务库 | PostgreSQL 15 |
| 向量库 | Milvus Standalone（通过 BaseVectorStore 抽象，后续可切 pgvector/Qdrant） |
| LLM/Embedding | OpenAI-compatible Client（httpx async，默认 qwen-plus） |
| SSE | sse-starlette |
| 配置 | pydantic-settings + YAML |
| 测试 | pytest + pytest-asyncio |
| Lint/Type | ruff + mypy |
| 依赖管理 | uv |
| 异步任务 | **FastAPI BackgroundTasks（MVP 锁定，不引入 Celery/Dramatiq/Redis Queue）** |

---

## 5. 分层架构

```
api  ──►  service  ──►  { domain, persistence, infra_ai, rag, ingestion, schemas }
                           │      │      │        │      │
                           │      │      │        │      └─► domain, infra_ai, persistence
                           │      │      │        └────────► domain, infra_ai, persistence
                           │      │      └─────────────────► domain
                           │      └────────────────────────► domain
                           └───────────────────────────────► (纯领域，零依赖)
所有层 ──► framework
```

### 5.1 各层职责

| 层 | 职责 |
|---|---|
| `api/` | FastAPI 路由层。**只调用 service**，使用 `schemas` 做请求/响应模型。不含业务逻辑。 |
| `schemas/` | **顶层独立**。Pydantic v2 API Schema（请求/响应模型、`ApiResponse[T]`、分页）。可依赖 `domain`，不被 domain 依赖。 |
| `service/` | **唯一编排中心**。编排 domain / persistence / infra_ai / rag / ingestion 完成业务用例。 |
| `domain/` | **纯领域**。只含 `enums.py` / `dto.py` / `value_objects.py`。零业务依赖。 |
| `persistence/` | 持久化层。`models/` 放 SQLAlchemy ORM Model，`repositories/` 放 Repository。依赖 `domain`。 |
| `infra_ai/` | AI 客户端抽象 + 实现（LLM / Embedding / Rerank）。依赖 `domain`。 |
| `rag/` | RAG 核心（vector / retrieve / prompt / memory）。依赖 `domain` + `infra_ai` + `persistence`（仅实现类）。 |
| `ingestion/` | 文档摄取（parser / chunker / pipeline）。依赖 `domain` + `infra_ai` + `persistence`。 |
| `framework/` | 通用基础设施（db / sse / trace / middleware / core）。被所有层依赖，本身不依赖业务层。 |

### 5.2 依赖硬约束

- `domain/` **不得 import** schemas / persistence / infra_ai / rag / ingestion / api / framework。
- `schemas/` 顶层独立，**不得被 domain 依赖**；可依赖 `domain`。
- `api/` **只调用 service**，禁止直接调用 repository / infra_ai / rag / ingestion。
- `persistence/models/` 是 ORM Model 唯一存放位置，禁止散落他处。
- **base 接口只依赖 domain**，禁止依赖 persistence。重点：`rag/memory/base.py`（BaseMemoryStore）不得 import persistence；`rag/vector/base.py`、`rag/retrieve/base.py`、`rag/retrieve/postprocessor/base.py` 同理。
- 实现类（如 `rag/memory/db_store.py`）才允许依赖 `persistence.repositories`。
- `framework/` 不得 import 任何业务层（domain / persistence / infra_ai / rag / ingestion / api / schemas）。

---

## 6. 关键设计决策

### 6.1 TraceSpan 策略（MVP）
- 第一批建 `t_trace_span` 表作为预留。
- MVP **仅实现** trace_id 透传（contextvars）+ `X-Trace-Id` 响应头 + 结构化日志（含 trace_id）。
- **不实现** 复杂 Span 树 / `@rag_trace_node` 装饰器 / 可视化追踪 / Span 写入。

### 6.2 异步摄取策略（MVP）
- T9 用 **FastAPI BackgroundTasks** 触发摄取 pipeline。
- **不引入** Celery / Dramatiq / Redis Queue。
- 任务失败仅更新 `Document.status = failed` + `error_message`，不重试、不死信、不重投。

### 6.3 Memory 策略（MVP）
- 仅实现 `load_history` + `append_message`。
- **不实现** `summarize` 摘要压缩（返回 None 或抛 NotImplemented）。

### 6.4 文档解析范围（MVP）
- 仅支持 TXT / Markdown / PDF。
- **暂缓** PPT / HTML / unstructured。

### 6.5 Rerank 策略（MVP）
- 仅实现 IdentityReranker（直通不排序）。
- **暂缓** Rerank 模型调用。

---

## 7. 禁止提前实现的暂缓项

在进入后续正式阶段前，**严禁**实现以下任何功能：

- MCP 工具集成
- 意图识别（树形分类 / IntentResolver）
- 多路检索（IntentDirected / VectorGlobal 多通道并行）
- 查询改写
- Rerank 模型（非 Identity）
- 三态熔断器 + 模型路由降级
- 队列式限流
- JWT 认证
- 复杂 Trace Span 树 / `@rag_trace_node` / 可视化追踪
- Memory summarize 摘要压缩
- PPT / HTML / unstructured 解析
- Celery / Dramatiq / Redis Queue 任务队列
- 管理后台 API（除 KB / 文档 CRUD 外）
- 对话标题生成

---

## 8. 编码规范要点

- 全 async，禁止同步阻塞 IO；需要调用同步库时用 `asyncio.to_thread`。
- trace_id 通过 contextvars 贯穿 async 链路，不得用全局变量。
- DB Model（SQLAlchemy）与 API Schema（Pydantic）严格分离，禁止混用。
- 表名 `t_` 前缀，主键用雪花 ID（`framework/core/snowflake.py`）。
- 异常三级：`BizException`（业务）/ `SysException`（系统）/ `InfraException`（基础设施），错误码段位 1xxxx / 2xxxx / 3xxxx。
- Prompt 模板放 `configs/prompts/`，禁止代码内硬编码。
- 密钥只走环境变量，`ModelProvider.api_key_ref` 存引用名不存明文。

---

## 9. 测试要求

- 单元测试禁止真实 IO（DB / Milvus / LLM 必须 Mock）。
- 集成测试依赖 docker-compose 启动的 PostgreSQL + Milvus。
- LLM 调用必须可 Mock（便于 CI）。
- 新增功能必须附带至少一个测试。

---

## 10. 提交规范

Conventional Commits，scope 用模块名：
```
feat(rag): 实现向量检索通道
fix(ingestion): 修复 PDF 分页元信息丢失
docs(readme): 更新 MVP 接口说明
optimize(infra-ai): LLM 流式首包探测
chore(persistence): 补充 TraceSpan 预留表迁移
```

---

## 11. 常见误区（AI 协作时易犯）

- ❌ 把 Java 的 `@Service`/`@Component` 翻译成 Python 装饰器堆砌 → ✅ 用 FastAPI 依赖注入
- ❌ 用线程池复刻原项目 8 个专用线程池 → ✅ 用 asyncio.gather + Semaphore
- ❌ MVP 阶段就引入 LlamaIndex/LangChain → ✅ MVP 直连 OpenAI-compatible Client + 手搓抽象
- ❌ 把领域模型和 API Schema 写成一个类 → ✅ DB Model 在 persistence/models，API Schema 在 schemas/，纯领域在 domain/
- ❌ 向量数据写入 PostgreSQL → ✅ 向量入 Milvus，业务元数据入 PostgreSQL，以 chunk.id 关联
- ❌ 把 API Schema 放 domain → ✅ schemas 顶层独立
- ❌ BaseMemoryStore base 接口依赖 persistence → ✅ base 只依赖 domain，实现类才依赖 persistence
- ❌ MVP 引入 Celery → ✅ 用 BackgroundTasks
- ❌ MVP 写 @rag_trace_node Span 树 → ✅ 仅 trace_id 透传
- ❌ 一次铺开 T1-T18 → ✅ 严格三批，逐批验收

---

## 12. 参考文档

- 原项目架构：https://github.com/nageoffer/ragent/blob/main/docs/ragent-architecture.md
- 原项目 README：https://github.com/nageoffer/ragent
- 本项目详细设计见 `docs/`
- 本项目规则约束见 `.trae/rules/`
