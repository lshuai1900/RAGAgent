# MVP_PLAN.md

> Ragent-Py 第一阶段 MVP 任务分批计划

---

## 1. 第 0 步：文档与规则落地（已完成）

### 范围
- AGENTS.md
- docs/（7 份设计文档）
- .trae/rules/（16 份规则文件）

### 开始条件
- 终版设计已确认

### 完成标准
- 24 份文件全部创建
- 内容与终版设计一致
- 不含任何业务代码

### 交付物
- 文档与规则体系，作为后续 Trae 编码的强约束

---

## 2. 第一批：T1-T4 项目骨架与基础设施

### 范围
| 任务 | 内容 |
|---|---|
| T1 | 项目骨架与依赖：uv、ruff、mypy、docker-compose（PG+Milvus）、空包结构、Makefile |
| T2 | 配置与基础设施：pydantic-settings + YAML、async engine、trace_id 中间件、结构化日志 |
| T3 | 持久化模型与迁移：7 张表 SQLAlchemy 2.0 Model + Alembic + BaseRepository |
| T4 | 异常、统一响应与 health：三级异常、ApiResponse、/health 接口 |

### 开始条件
- 第 0 步验收通过

### 完成标准
- `uv sync` 成功
- `make lint`（ruff）零警告
- `make typecheck`（mypy）零错误
- `docker-compose up` 拉起 PostgreSQL + Milvus
- `alembic upgrade head` 在空库成功建 7 张表
- `GET /health` 返回 200 + DB/Milvus 连通性
- 全局异常拦截器把所有异常包装为 ApiResponse
- trace_id 透传 + X-Trace-Id 响应头 + 结构化日志含 trace_id
- 按终版目录结构创建所有空包与 __init__.py

### 交付物
可启动的空 FastAPI 应用 + /health + 数据库 schema（含 TraceSpan 预留表）+ 异常响应体系 + trace_id 透传。**无业务接口。**

---

## 3. 第二批：T5-T9 文档摄取链路

### 范围
| 任务 | 内容 |
|---|---|
| T5 | 文档解析（TXT/MD/PDF）：BaseDocumentParser + 3 实现 + registry |
| T6 | 分块器：BaseChunker + Recursive/Sentence/Fixed 3 实现 |
| T7 | Embedding 客户端：BaseEmbeddingClient + OpenAI-compatible 实现 + factory |
| T8 | Milvus 向量库：BaseVectorStore + Milvus 实现 |
| T9 | 摄取 Pipeline + 文档/KB API：线性 pipeline + BackgroundTasks 触发 + KB CRUD + 文档上传 |

### 开始条件
- 第一批 T1-T4 全部验收通过

### 完成标准
- BaseDocumentParser 定义，Txt/Markdown/Pdf 3 种实现，registry 按 file_type 路由
- BaseChunker 定义，Recursive/Sentence/Fixed 3 实现，单测覆盖边界
- BaseEmbeddingClient 定义，OpenAI-compatible 实现（httpx async），可 Mock
- BaseVectorStore 定义，Milvus 实现，ensure_collection/upsert/search/delete_by_document 可用
- 摄取 pipeline 线性编排 parse→chunk→embed→index
- Document 状态机 pending→...→completed/failed
- Chunk 落 PG + 向量入 Milvus（以 chunk.id 关联）
- 文件 SHA256 hash 去重
- **用 FastAPI BackgroundTasks 触发 pipeline**（不引入 Celery）
- 任务失败仅更新 Document.status=failed + error_message
- KB CRUD 接口可用
- 文档上传 multipart 接口可用，立即返回 document_id，后台异步处理
- 文档列表 + 状态查询可用

### 交付物
可上传 TXT/MD/PDF → BackgroundTasks 异步分块入库 → Milvus 可检索 + PG 有元数据。**无问答能力。**

---

## 4. 第三批：T10-T12、T14-T15、T18 检索与流式问答端到端

### 范围
| 任务 | 内容 |
|---|---|
| T10 | 检索器与后处理：BaseRetriever + VectorRetriever + DedupPostProcessor + IdentityReranker |
| T11 | LLM 客户端：BaseLLMClient + OpenAI-compatible 实现（httpx async + SSE 解析 + 首包探测） |
| T12 | Prompt 模板服务：configs/prompts/ + PromptService 渲染 |
| T14 | Chat Service 编排：load_history → retrieve → prompt → stream_chat（简化 Memory，无 summarize） |
| T15 | SSE 流式接口：POST /api/v1/chat/sse（start/delta/done/error 事件） |
| T18 | 端到端测试：上传 sample.pdf → 问答 → 流式回答 |

### 开始条件
- 第二批 T5-T9 全部验收通过

### 完成标准
- BaseRetriever 定义，VectorRetriever 实现（embed query → Milvus search → RetrievalResult）
- BasePostProcessor 定义，DedupPostProcessor 按 chunk_id 去重保留最高分
- IdentityReranker 直通
- BaseLLMClient 定义，OpenAI-compatible 实现，stream_chat 返回 AsyncIterator[ChatChunk]
- 首包事件可探测
- PromptService 加载并渲染 {key} 占位符，禁止硬编码
- chat_service.py 编排：load_history → retrieve → prompt → stream_chat
- ChatMessage 持久化 user + assistant，retrieval_context 落库
- trace_id 贯穿（仅 contextvars 透传，不写 Span 树）
- POST /api/v1/chat/sse 返回 sse-starlette 事件流
- 事件格式：start/delta/done/error，错误事件带 trace_id
- 连接断开不导致进程崩溃
- 集成测试：上传 sample.pdf → 等待 completed → 调 /api/v1/chat/sse → 收到基于文档内容的流式回答
- ChatMessage 表有 user+assistant 记录，retrieval_context 非空
- 全流程 async 无阻塞
- LLM 调用可 Mock 跑 CI

### 交付物
完整 MVP 闭环——上传文档 → 单轮流式问答（向量检索 + LLM SSE）。

---

## 5. 暂缓任务清单

以下任务**不在 MVP 三批范围内**，留待后续阶段：

| 暂缓项 | 后续阶段 | 暂缓原因 |
|---|---|---|
| 复杂 Trace Span 树 / @rag_trace_node / 可视化追踪 | P7 生产特性 | MVP 仅 trace_id 透传 |
| Memory summarize 摘要压缩 | P6 对话记忆 | MVP 仅 load/append |
| PPT / HTML / unstructured 解析 | P2 摄取管道扩展 | MVP 仅 TXT/MD/PDF |
| JWT 认证 | P7 生产特性 | MVP 无认证 |
| MCP 工具集成 | P5 MCP | 非 MVP 范围 |
| 三态熔断器 + 模型路由降级 | P7 生产特性 | 非 MVP 范围 |
| 队列式限流 | P7 生产特性 | 非 MVP 范围 |
| Rerank 模型（非 Identity） | P4 多路检索 | MVP 仅 Identity |
| 意图识别（树形分类 / IntentResolver） | P3 意图识别 | 非 MVP 范围 |
| 多路检索（IntentDirected / VectorGlobal） | P4 多路检索 | 非 MVP 范围 |
| 查询改写（QueryRewrite） | P4 多路检索 | 非 MVP 范围 |
| Celery / Dramatiq / Redis Queue 任务队列 | P2 摄取管道 | MVP 用 BackgroundTasks |
| 管理后台 API（除 KB/文档 CRUD 外） | P8 管理后台 | 非 MVP 范围 |
| 对话标题生成 | P6 对话记忆 | 非 MVP 范围 |
| 多知识库路由 | P3 意图识别 | MVP 单知识库 |

---

## 6. 当前开源状态

MVP 三批代码已随仓库保留，开源整理阶段以发布卫生为主：

- 保留后端、前端、迁移、配置模板、Prompt 模板、测试与设计文档。
- 不保留本地运行数据、缓存、虚拟环境、前端依赖安装目录和构建产物。
- 不新增 MVP 暂缓功能。
- 发布前以 lint、typecheck、单元测试和必要的集成测试作为验收依据。

---

## 7. 三批推进纪律

1. **严格按批推进**：每批完成后必须通过验收检查，才能启动下一批。
2. **禁止提前实现**：在当前批次未完成前，不得实现后续批次功能。
3. **禁止提前实现暂缓项**：MVP 三批任务完成前，严禁实现暂缓清单中的任何功能。
4. **每批验收**：每批完成后输出新增文件清单、运行命令、验收结果。
5. **每批提交**：每批完成后按 Conventional Commits 规范提交。

详细验收标准见 [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md)。
