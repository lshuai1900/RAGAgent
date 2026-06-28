# ACCEPTANCE_CRITERIA.md

> Ragent-Py 验收标准（第 0 步 + 三批任务）

---

## 第 0 步：文档与规则落地

### 验收项

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 0.1 | AGENTS.md | 已创建；含项目定位、当前阶段、后续阶段、技术栈、分层架构、domain 边界、schemas 独立、persistence、api 只调 service、base 接口只依赖 domain、MVP trace_id 策略、BackgroundTasks 策略、暂缓项清单 |
| 0.2 | docs/PROJECT_SPEC.md | 已创建；含项目背景、与 ragent 关系、Python 复刻原则、MVP 目标、非目标、技术栈、三批交付范围 |
| 0.3 | docs/ARCHITECTURE.md | 已创建；含分层架构图、每层职责、依赖方向、禁止依赖规则、service 编排中心、framework 基础设施、domain 纯领域、schemas 独立、persistence 层 |
| 0.4 | docs/MVP_PLAN.md | 已创建；含第 0 步、第一批 T1-T4、第二批 T5-T9、第三批 T10-T12/T14-T15/T18、每批开始条件、每批完成标准、暂缓任务清单 |
| 0.5 | docs/DATA_MODEL.md | 已创建；含 7 张表（KnowledgeBase/Document/Chunk/ChatSession/ChatMessage/TraceSpan 预留/ModelProvider）完整字段设计 |
| 0.6 | docs/INTERFACES.md | 已创建；含 9 个抽象接口（BaseDocumentParser/BaseChunker/BaseEmbeddingClient/BaseVectorStore/BaseRetriever/BasePostProcessor/BaseReranker/BaseLLMClient/BaseMemoryStore）归属与契约 |
| 0.7 | docs/DEVELOPMENT_WORKFLOW.md | 已创建；含编码前必读、批次推进纪律、修改前输出、修改后输出、编码规范检查清单、异常处理流程 |
| 0.8 | docs/ACCEPTANCE_CRITERIA.md | 已创建；含第 0 步 + 三批完整验收标准 |
| 0.9 | .trae/rules/ 16 个 .mdc 文件 | 全部创建；每个含适用范围、允许行为、禁止行为、硬约束 |
| 0.10 | 无业务代码 | 未实现任何 FastAPI 路由 / SQLAlchemy Model / Alembic 迁移 / Milvus / Embedding / LLM / RAG / 文档解析 / SSE / Memory / TraceSpan 写入 |

### 第 0 步完成标志
- 24 份文件全部创建且内容完整
- 与终版设计一致
- 不含任何业务代码
- 可作为后续 Trae 编码的强约束

---

## 第一批：T1-T4 项目骨架与基础设施

### T1 项目骨架与依赖

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 1.1 | uv 依赖管理 | `pyproject.toml` 存在；`uv sync` 成功；`uv.lock` 生成 |
| 1.2 | ruff 配置 | `ruff` 配置存在；`make lint` 或 `uv run ruff check` 零警告 |
| 1.3 | mypy 配置 | `mypy` 配置存在；`make typecheck` 或 `uv run mypy src` 零错误 |
| 1.4 | docker-compose | `docker-compose.yml` 存在；`docker-compose up` 拉起 PostgreSQL + Milvus Standalone |
| 1.5 | 目录结构 | 按终版目录结构创建所有空包与 `__init__.py`（api/schemas/service/domain/persistence/infra_ai/rag/ingestion/framework） |
| 1.6 | Makefile | `Makefile` 含 lint/typecheck/test/dev/migrate 快捷命令 |
| 1.7 | .env.example | 存在；含 DB_URL/MILVUS_URI/LLM_API_KEY 等占位 |

### T2 配置与基础设施

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 2.1 | 配置加载 | `framework/core/config.py` 用 pydantic-settings 加载 `configs/config.yaml`；支持环境变量覆盖 |
| 2.2 | async engine | `framework/db/session.py` async engine + async session factory；连通 PG（健康检查 SQL 通过） |
| 2.3 | trace_id 中间件 | `framework/middleware/trace.py` 每个 HTTP 请求注入 trace_id（contextvars）；写入响应头 `X-Trace-Id` |
| 2.4 | 结构化日志 | `framework/core/logging.py` structlog 结构化日志；日志含 trace_id |
| 2.5 | snowflake ID | `framework/core/snowflake.py` 雪花 ID 生成器可用 |

### T3 持久化模型与迁移

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 3.1 | ORM Model 位置 | 7 张表 SQLAlchemy 2.0 Model 全部位于 `persistence/models/` |
| 3.2 | 公共 mixin | `persistence/models/base.py` 含 declarative base + 公共字段 mixin（id 雪花 / created_at / updated_at） |
| 3.3 | 表名规范 | 所有表名 `t_` 前缀 |
| 3.4 | 7 张表完整 | KnowledgeBase / Document / Chunk / ChatSession / ChatMessage / TraceSpan（预留）/ ModelProvider 字段与 DATA_MODEL.md 一致 |
| 3.5 | Alembic 迁移 | `alembic/env.py` 配置 async；`alembic upgrade head` 在空库成功建 7 张表 |
| 3.6 | BaseRepository | `persistence/repositories/base.py` 泛型 BaseRepository 可用（CRUD 基础方法） |

### T4 异常、统一响应与 health

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 4.1 | 三级异常 | `framework/core/exceptions.py` 含 BizException / SysException / InfraException + 错误码段位（1xxxx/2xxxx/3xxxx） |
| 4.2 | 全局异常拦截 | `framework/middleware/exception.py` 全局拦截器把所有异常包装为 ApiResponse；未捕获异常返回 500 且不泄露堆栈 |
| 4.3 | ApiResponse | `schemas/common.py` 含 `ApiResponse[T]` 泛型响应体 |
| 4.4 | health 接口 | `GET /health` 返回 200 + DB/Milvus 连通性状态 |
| 4.5 | FastAPI 启动 | `src/ragent/main.py` FastAPI app + lifespan + 路由挂载；`make dev` 可启动 |
| 4.6 | TraceSpan 预留 | `t_trace_span` 表已建，但**未写入任何 Span 数据**（MVP 不实现 Span 树） |

### 第一批完成标志
- 可启动的空 FastAPI 应用
- `/health` 返回 200 + 依赖连通性
- 数据库 schema 就绪（7 张表，含 TraceSpan 预留）
- 异常响应体系可用
- trace_id 透传 + X-Trace-Id 响应头 + 结构化日志
- **无业务接口**

---

## 第二批：T5-T9 文档摄取链路

### T5 文档解析（TXT/MD/PDF）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 5.1 | BaseDocumentParser | 定义于 `ingestion/parser/base.py`；只依赖 `domain.dto.ParsedDocument`；未依赖 persistence |
| 5.2 | TxtParser | `ingestion/parser/txt.py` 实现可用 |
| 5.3 | MarkdownParser | `ingestion/parser/markdown.py` 实现可用，保留章节元信息 |
| 5.4 | PdfParser | `ingestion/parser/pdf.py` 实现可用，保留页码元信息 |
| 5.5 | registry | `ingestion/parser/registry.py` 按 file_type 路由 |
| 5.6 | 单元测试 | 覆盖空文件/超长文件/正常文件 |

### T6 分块器

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 6.1 | BaseChunker | 定义于 `ingestion/chunker/base.py`；只依赖 `domain.dto.ChunkDraft` / `domain.value_objects.ChunkConfig`；未依赖 persistence |
| 6.2 | RecursiveChunker | `ingestion/chunker/recursive.py` 实现（默认策略） |
| 6.3 | SentenceChunker | `ingestion/chunker/sentence.py` 实现 |
| 6.4 | FixedSizeChunker | `ingestion/chunker/fixed.py` 实现 |
| 6.5 | 分块结果 | 含 chunk_index 与 metadata |
| 6.6 | 单元测试 | 覆盖空文本/超长/overlap 正确性 |

### T7 Embedding 客户端

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 7.1 | BaseEmbeddingClient | 定义于 `infra_ai/embedding/base.py`；只依赖 `domain`；未依赖 persistence |
| 7.2 | OpenAI-compatible 实现 | `infra_ai/embedding/openai_compat.py` 实现（httpx async） |
| 7.3 | 接口完整 | `embed`/`embed_one`/`dim`/`model_name` 接口可用 |
| 7.4 | 批量请求 | 批量向量化支持 |
| 7.5 | factory | `infra_ai/factory.py` 按 ModelProvider 配置构建客户端 |
| 7.6 | 可 Mock | LLM/Embedding 调用可 Mock（便于 CI） |

### T8 Milvus 向量库

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 8.1 | BaseVectorStore | 定义于 `rag/vector/base.py`；只依赖 `domain.dto.VectorRecord`/`VectorHit`；**未依赖 persistence** |
| 8.2 | Milvus 实现 | `rag/vector/milvus.py` 实现（pymilvus async） |
| 8.3 | ensure_collection | 幂等创建（按 embedding_dim 建 schema） |
| 8.4 | upsert | 批量写入/更新可用 |
| 8.5 | search | 向量近邻检索可用 |
| 8.6 | delete_by_document | 按文档删除可用 |
| 8.7 | drop_collection | 删除 collection 可用 |
| 8.8 | 集成测试 | 连真实 Milvus 通过 |

### T9 摄取 Pipeline + 文档/KB API（BackgroundTasks）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 9.1 | 线性 pipeline | `ingestion/pipeline.py` 编排 parse→chunk→embed→index |
| 9.2 | Document 状态机 | pending→parsing→chunking→embedding→indexing→completed/failed 流转 |
| 9.3 | Chunk 落库 | Chunk 落 PG（t_document_chunk）+ 向量入 Milvus（以 chunk.id 关联） |
| 9.4 | 文件去重 | 文件 SHA256 hash 去重 |
| 9.5 | BackgroundTasks | **用 FastAPI BackgroundTasks 触发 pipeline**；未引入 Celery/Dramatiq/Redis Queue |
| 9.6 | 失败处理 | 任务失败仅更新 `Document.status=failed` + `error_message`；不重试/不死信 |
| 9.7 | knowledge_service | `service/knowledge_service.py` 编排 KB CRUD |
| 9.8 | ingestion_service | `service/ingestion_service.py` 编排文档上传 + 触发 pipeline |
| 9.9 | KB API | `api/v1/knowledge_bases.py` KB CRUD 接口可用（api 只调 service） |
| 9.10 | 文档上传 API | `api/v1/documents.py` 上传 multipart 接口可用；立即返回 document_id；后台异步处理 |
| 9.11 | 文档列表/状态 | 文档列表分页 + 状态查询可用 |
| 9.12 | api 只调 service | api 层未直接调 repository/infra_ai/rag/ingestion |

### 第二批完成标志
- 可上传 TXT/MD/PDF → BackgroundTasks 异步分块入库
- Milvus 可检索 + PG 有元数据
- KB CRUD 可用
- 文档上传/列表/状态查询可用
- **无问答能力**

---

## 第三批：T10-T12、T14-T15、T18 检索与流式问答端到端

### T10 检索器与后处理

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 10.1 | BaseRetriever | 定义于 `rag/retrieve/base.py`；只依赖 `domain`；**未依赖 persistence** |
| 10.2 | VectorRetriever | `rag/retrieve/vector_retriever.py` 实现（embed query → Milvus search → 映射 RetrievalResult） |
| 10.3 | BasePostProcessor | 定义于 `rag/retrieve/postprocessor/base.py`；只依赖 `domain.dto.RetrievalResult`；**未依赖 persistence** |
| 10.4 | DedupPostProcessor | `rag/retrieve/postprocessor/dedup.py` 按 chunk_id 去重保留最高分 |
| 10.5 | IdentityReranker | `infra_ai/rerank/identity.py` 直通不排序（MVP 仅此实现） |
| 10.6 | kb_id 过滤 | 检索支持按 kb_id 过滤 |
| 10.7 | top_k 可配 | top_k 参数可配置 |

### T11 LLM 客户端

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 11.1 | BaseLLMClient | 定义于 `infra_ai/llm/base.py`；只依赖 `domain.dto.ChatChunk`/`domain.value_objects.ChatOptions`；未依赖 persistence |
| 11.2 | OpenAI-compatible 实现 | `infra_ai/llm/openai_compat.py` 实现（httpx async + SSE 解析） |
| 11.3 | chat 非流式 | `chat` 接口可用 |
| 11.4 | stream_chat 流式 | `stream_chat` 返回 `AsyncIterator[ChatChunk]` |
| 11.5 | 首包探测 | 首包事件可探测（用于 SSE start 事件） |
| 11.6 | ChatOptions | temperature/top_p/max_tokens/stop 可配 |
| 11.7 | 可 Mock | LLM 调用可 Mock（便于 CI） |

### T12 Prompt 模板服务

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 12.1 | 模板目录 | `configs/prompts/` 存在；含 answer-chat-kb.txt / context-format.txt |
| 12.2 | PromptService | `rag/prompt/service.py` 加载并渲染 `{key}` 占位符 |
| 12.3 | KB 回答模板 | 含 evidence + question 拼装 |
| 12.4 | 禁止硬编码 | 代码内无硬编码 Prompt 字符串 |

### T14 Chat Service 编排（简化版）

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 14.1 | chat_service | `service/chat_service.py` 编排：load_history → retrieve → prompt → stream_chat |
| 14.2 | 全程 async | 无阻塞调用 |
| 14.3 | Memory 简化 | BaseMemoryStore 仅 load_history/append_message；**未实现 summarize**（返回 None） |
| 14.4 | ChatMessage 持久化 | user + assistant 消息落库 |
| 14.5 | retrieval_context | 关联检索结果落库 |
| 14.6 | trace_id 贯穿 | 仅 contextvars 透传；**未写 Span 树** |

### T15 SSE 流式接口

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 15.1 | 接口可用 | `POST /api/v1/chat/sse` 返回 sse-starlette 事件流 |
| 15.2 | 事件格式 | start/delta/done/error 四类事件 |
| 15.3 | 首包延迟 | 首包事件可观测 |
| 15.4 | 错误事件 | 携带 trace_id |
| 15.5 | 连接断开 | 不导致进程崩溃 |
| 15.6 | api 只调 service | api 层未直接调 infra_ai/rag |

### T18 端到端测试

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| 18.1 | 集成测试 | 上传 sample.pdf → 等待 completed → 调 `/api/v1/chat/sse` → 收到基于文档内容的流式回答 |
| 18.2 | ChatMessage 记录 | 表有 user+assistant 记录 |
| 18.3 | retrieval_context | 非空 |
| 18.4 | 全流程 async | 无阻塞 |
| 18.5 | LLM 可 Mock | LLM 调用可 Mock 跑 CI |

### 第三批完成标志
- 完整 MVP 闭环：上传文档 → 单轮流式问答（向量检索 + LLM SSE）
- ChatMessage 持久化 + retrieval_context 落库
- 端到端集成测试通过
- LLM 可 Mock 跑 CI

---

## 总验收（MVP 完成）

MVP 三批全部完成后，需满足：

- [ ] 第一批 T1-T4 全部验收通过
- [ ] 第二批 T5-T9 全部验收通过
- [ ] 第三批 T10-T12、T14-T15、T18 全部验收通过
- [ ] 未实现任何暂缓项（MCP/意图/多路检索/Rerank 模型/熔断/限流/JWT/复杂 Trace/Celery/管理后台等）
- [ ] lint 零警告、typecheck 零错误、测试全通过
- [ ] 端到端闭环可演示
