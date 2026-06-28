# ARCHITECTURE.md

> Ragent-Py 分层架构与依赖规则说明

---

## 1. 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                          api/                                │
│   FastAPI 路由层（只调 service，用 schemas 做请求/响应）       │
└──────────────────────────┬──────────────────────────────────┘
                           │ 只调用 service
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       service/                               │
│   唯一编排中心（编排 domain/persistence/infra_ai/rag/ingestion）│
└──┬───────┬──────────┬───────────┬──────────┬───────────────┘
   │       │          │           │          │
   ▼       ▼          ▼           ▼          ▼
┌──────┐ ┌────────┐ ┌─────────┐ ┌─────┐ ┌──────────┐
│domain│ │persist-│ │infra_ai │ │ rag │ │ingestion │
│      │ │ ence   │ │         │ │     │ │          │
│纯领域│ │ORM+Repo│ │AI客户端 │ │RAG  │ │文档摄取   │
└──┬───┘ └───┬────┘ └────┬────┘ └──┬──┘ └─────┬────┘
   │         │           │          │          │
   │         │           │          │          │
   ▼         ▼           ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                       schemas/                               │
│   顶层独立 Pydantic v2 API Schema（可依赖 domain）             │
└─────────────────────────────────────────────────────────────┘

所有层 ──► framework/（通用基础设施，不依赖业务层）
```

简化依赖链：

```
api  ──►  service  ──►  { domain, persistence, infra_ai, rag, ingestion, schemas }
所有层 ──►  framework
```

---

## 2. 每层职责

### 2.1 api/（路由层）
- FastAPI 路由定义，按版本分层 `api/v1/`
- **只调用 service**，不直接调用 repository / infra_ai / rag / ingestion
- 使用 `schemas/` 的 Pydantic 模型做请求体校验与响应序列化
- 通过 `api/deps.py` 做依赖注入（注入 service）
- 不含业务逻辑，只做 HTTP 编排

### 2.2 schemas/（API Schema，顶层独立）
- Pydantic v2 模型：请求 Schema、响应 Schema、`ApiResponse[T]`、分页响应
- **顶层独立**，不属于 domain
- 可依赖 `domain`（使用枚举、DTO）
- 不得被 `domain` 依赖
- 严格与 SQLAlchemy ORM Model 分离

### 2.3 service/（编排中心）
- **唯一编排中心**，业务用例的入口
- 编排 domain / persistence / infra_ai / rag / ingestion 完成业务流程
- 例如 `chat_service.py` 编排：load_history → retrieve → prompt → stream_chat
- 依赖所有下层，但不被 api 以外的层依赖

### 2.4 domain/（纯领域）
- **纯领域，零业务依赖**
- 只含三个文件：
  - `enums.py`：枚举（DocumentStatus / ChunkEmbeddingStatus / MessageRole / ProviderType / KnowledgeBaseStatus）
  - `dto.py`：跨层共享值对象（ParsedDocument / ChunkDraft / VectorRecord / VectorHit / RetrievalResult / ChatChunk）
  - `value_objects.py`：值对象（ChunkConfig / ChatOptions / RetrievalQuery）
- **不得 import** schemas / persistence / infra_ai / rag / ingestion / api / framework

### 2.5 persistence/（持久化层）
- `models/`：SQLAlchemy 2.0 declarative ORM Model（唯一存放位置）
- `repositories/`：Repository 数据访问层，含泛型 `BaseRepository`
- 依赖 `domain`（使用 DTO / 枚举）
- 公共字段 mixin：id（雪花）/ created_at / updated_at / deleted_at（软删除）
- 表名 `t_` 前缀

### 2.6 infra_ai/（AI 客户端）
- `llm/`：BaseLLMClient + OpenAI-compatible 实现
- `embedding/`：BaseEmbeddingClient + OpenAI-compatible 实现
- `rerank/`：BaseReranker + IdentityReranker（MVP）
- `factory.py`：按 ModelProvider 配置构建客户端
- 依赖 `domain`（使用 DTO / 值对象）
- base 接口只依赖 domain，不依赖 persistence

### 2.7 rag/（RAG 核心）
- `vector/`：BaseVectorStore + Milvus 实现
- `retrieve/`：BaseRetriever + VectorRetriever + postprocessor（Dedup）
- `prompt/`：PromptService（模板加载与渲染）
- `memory/`：BaseMemoryStore + DbMemoryStore
- 依赖 `domain` + `infra_ai` 抽象 + `persistence`（**仅实现类**）
- **base 接口只依赖 domain**，禁止依赖 persistence

### 2.8 ingestion/（文档摄取）
- `parser/`：BaseDocumentParser + Txt/Markdown/Pdf 实现 + registry
- `chunker/`：BaseChunker + Recursive/Sentence/Fixed 实现
- `pipeline.py`：线性 pipeline（parse → chunk → embed → index）
- 依赖 `domain` + `infra_ai` + `persistence`

### 2.9 framework/（通用基础设施）
- `core/`：config（pydantic-settings）/ exceptions（三级异常）/ response（ApiResponse）/ snowflake / logging
- `db/`：async engine / session
- `sse/`：SSE 事件流封装
- `trace/`：trace_id 透传（contextvars，MVP 不实现 Span 树）
- `middleware/`：异常拦截 / trace_id 注入
- **被所有层依赖，本身不依赖任何业务层**

---

## 3. 依赖方向

### 3.1 允许的依赖方向

```
api           ──►  service, schemas, framework
service       ──►  domain, persistence, infra_ai, rag, ingestion, schemas, framework
schemas       ──►  domain, framework
persistence   ──►  domain, framework
infra_ai      ──►  domain, framework
rag           ──►  domain, infra_ai, persistence(仅实现类), framework
ingestion     ──►  domain, infra_ai, persistence, framework
domain        ──►  (无，纯领域)
framework     ──►  (无业务依赖)
```

### 3.2 禁止的依赖（硬约束）

| 层 | 禁止 import |
|---|---|
| `domain/` | schemas / persistence / infra_ai / rag / ingestion / api / framework |
| `schemas/` | persistence / infra_ai / rag / ingestion / api（可依赖 domain） |
| `api/` | persistence / infra_ai / rag / ingestion（只能调 service） |
| `framework/` | domain / persistence / infra_ai / rag / ingestion / api / schemas |
| `base 接口`（各层 base.py） | persistence（重点：BaseMemoryStore / BaseVectorStore / BaseRetriever / BasePostProcessor） |

### 3.3 实现类依赖豁免

实现类（非 base 接口）允许依赖 persistence，例如：
- `rag/memory/db_store.py`（DbMemoryStore）可依赖 `persistence.repositories`
- `rag/vector/milvus.py`（MilvusVectorStore）可依赖 infra_ai / domain
- `rag/retrieve/vector_retriever.py` 可依赖 `infra_ai` + `rag.vector`

---

## 4. service 作为唯一编排中心

`service/` 是业务用例的唯一入口，所有跨层编排在此完成：

| Service | 职责 |
|---|---|
| `knowledge_service.py` | 知识库 CRUD 编排 |
| `ingestion_service.py` | 文档上传 → 触发 BackgroundTasks → 摄取 pipeline 编排 |
| `chat_service.py` | 问答编排：load_history → retrieve → prompt → stream_chat |

**硬约束**：
- api 层只能调用 service，不得绕过 service 直接调 repository / infra_ai / rag / ingestion
- service 之间可以互相调用（如 chat_service 调 ingestion_service 查文档状态）
- service 不含 HTTP 语义（不返回 Response 对象，不感知 status_code）

---

## 5. framework 作为通用基础设施

`framework/` 提供与业务无关的通用能力：

| 子包 | 内容 |
|---|---|
| `core/config.py` | pydantic-settings 配置加载 |
| `core/exceptions.py` | 三级异常（BizException / SysException / InfraException）+ 错误码 |
| `core/response.py` | ApiResponse[T] 统一响应体 |
| `core/snowflake.py` | 雪花 ID 生成器 |
| `core/logging.py` | structlog 结构化日志（含 trace_id） |
| `db/session.py` | async engine + async session factory |
| `sse/emitter.py` | SSE 事件流封装 |
| `trace/context.py` | trace_id 透传（contextvars，MVP 不实现 Span 树） |
| `middleware/exception.py` | 全局异常拦截器 |
| `middleware/trace.py` | trace_id 注入 + X-Trace-Id 响应头 |

**硬约束**：framework 不得 import 任何业务层。

---

## 6. domain 纯领域

`domain/` 是纯领域层，零业务依赖：

```
domain/
├── enums.py          # 枚举
├── dto.py            # 跨层共享值对象
└── value_objects.py  # 值对象
```

### 6.1 enums.py
- DocumentStatus（pending/parsing/chunking/embedding/indexing/completed/failed）
- ChunkEmbeddingStatus（pending/embedded/indexed/failed）
- MessageRole（user/assistant）
- ProviderType（qwen/openai/deepseek）
- KnowledgeBaseStatus（active/archived）

### 6.2 dto.py
- ParsedDocument（text, sections, metadata）
- ChunkDraft（content, chunk_index, metadata）
- VectorRecord（id, vector, content, metadata）
- VectorHit（id, score, content, metadata）
- RetrievalResult（chunk_id, document_id, kb_id, content, score, metadata, retrieval_channel, rerank_score）
- ChatChunk（delta, finish_reason）

### 6.3 value_objects.py
- ChunkConfig（chunk_size, overlap, separators）
- ChatOptions（temperature, top_p, max_tokens, stop）
- RetrievalQuery（text, kb_id, session_id）

**硬约束**：domain 不得 import 任何其他业务层 / framework / schemas。

---

## 7. schemas 顶层独立

`schemas/` 是顶层独立的 Pydantic v2 API Schema 层：

```
schemas/
├── common.py            # ApiResponse[T]、PageResponse[T]
├── knowledge_base.py    # KB 请求/响应 Schema
├── document.py          # 文档请求/响应 Schema
└── chat.py              # 问答请求/响应 Schema
```

**为什么独立**：
- API Schema 是接口契约，与领域模型关注点不同
- 避免 domain 被 Pydantic 污染（domain 保持纯数据结构）
- 避免 ORM Model 与 API Schema 混用（常见反模式）

**硬约束**：
- schemas 可依赖 domain（用枚举/DTO）
- schemas 不得被 domain 依赖
- schemas 不得 import persistence / infra_ai / rag / ingestion / api

---

## 8. persistence 持久化层

`persistence/` 是数据持久化层：

```
persistence/
├── models/              # SQLAlchemy 2.0 declarative ORM Model（唯一位置）
│   ├── base.py          # declarative base + 公共字段 mixin
│   ├── knowledge_base.py
│   ├── document.py
│   ├── chunk.py
│   ├── chat_session.py
│   ├── chat_message.py
│   ├── trace_span.py    # 预留表（MVP 不写 Span）
│   └── model_provider.py
└── repositories/        # Repository 数据访问层
    ├── base.py          # 泛型 BaseRepository
    ├── knowledge_base_repo.py
    ├── document_repo.py
    ├── chunk_repo.py
    ├── chat_repo.py
    └── model_provider_repo.py
```

**硬约束**：
- ORM Model 只能放 `persistence/models/`，禁止散落他处
- ORM Model 与 Pydantic Schema 严禁混用
- Repository 走 `persistence/repositories/`，通过 BaseRepository 泛型复用
- 表名 `t_` 前缀，主键雪花 ID，`created_at/updated_at` 自动填充

详细字段设计见 [DATA_MODEL.md](./DATA_MODEL.md)。
