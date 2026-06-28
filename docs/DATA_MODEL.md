# DATA_MODEL.md

> Ragent-Py 数据模型设计（7 张表）
>
> 所有表位于 `persistence/models/`，使用 SQLAlchemy 2.0 async declarative。
> 公共字段 mixin：`id`（雪花 ID，str 主键）、`created_at`、`updated_at`。
> 表名统一 `t_` 前缀。

---

## 1. t_knowledge_base（知识库）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | 知识库 ID |
| name | String(128) | not null, unique | 名称 |
| description | String(512) | nullable | 描述 |
| collection_name | String(128) | not null | Milvus collection 名（命名规范：`kb_{id}`） |
| embedding_dim | Integer | not null, default 1024 | 向量维度（决定 Milvus schema） |
| embedding_model | String(64) | not null | Embedding 模型标识 |
| chunk_strategy | String(32) | not null, default "recursive" | 分块策略 |
| chunk_size | Integer | default 512 | 分块大小 |
| chunk_overlap | Integer | default 64 | 重叠 |
| document_count | Integer | default 0 | 文档数（冗余计数） |
| status | String(16) | default "active" | active / archived（KnowledgeBaseStatus 枚举） |
| created_at | DateTime | not null | 创建时间 |
| updated_at | DateTime | not null | 更新时间 |

**索引**：unique(name)

---

## 2. t_document（文档）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | 文档 ID |
| kb_id | String | FK → t_knowledge_base.id, not null | 所属知识库 |
| name | String(256) | not null | 文件名 |
| file_type | String(16) | not null | pdf / docx / pptx / html / md / txt（MVP 仅 txt/md/pdf） |
| file_size | Integer | not null | 字节数 |
| file_hash | String(64) | not null, indexed | SHA256，用于去重/幂等 |
| status | String(16) | default "pending" | pending/parsing/chunking/embedding/indexing/completed/failed（DocumentStatus 枚举） |
| chunk_count | Integer | default 0 | 分块数 |
| total_tokens | Integer | default 0 | 估算 token 数 |
| error_message | Text | nullable | 失败原因 |
| created_at | DateTime | not null | |
| updated_at | DateTime | not null | |

**索引**：index(kb_id), index(file_hash), index(status)

---

## 3. t_document_chunk（文档分块）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | 分块 ID（同时作为 Milvus 主键） |
| document_id | String | FK → t_document.id, not null | 所属文档 |
| kb_id | String | FK → t_knowledge_base.id, not null | 所属知识库（冗余，便于按 KB 检索） |
| content | Text | not null | 分块文本 |
| chunk_index | Integer | not null | 文档内序号 |
| token_count | Integer | default 0 | 该块 token 数 |
| char_count | Integer | default 0 | 字符数 |
| metadata | JSONB | default {} | 来源页码/章节/标题等结构化信息 |
| embedding_status | String(16) | default "pending" | pending/embedded/indexed/failed（ChunkEmbeddingStatus 枚举） |
| created_at | DateTime | not null | |

**索引**：index(document_id), index(kb_id), index(embedding_status)

> **注意**：向量本身不入 PostgreSQL，存于 Milvus，以 chunk.id 关联。

---

## 4. t_chat_session（会话）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | 会话 ID |
| title | String(128) | nullable | 会话标题（MVP 可空，后续 LLM 生成） |
| kb_id | String | FK → t_knowledge_base.id, nullable | 关联知识库（MVP 单 KB，后续可空） |
| user_id | String(64) | nullable | 用户 ID（MVP 暂无认证，预留） |
| message_count | Integer | default 0 | 消息数 |
| status | String(16) | default "active" | active / archived |
| created_at | DateTime | not null | |
| updated_at | DateTime | not null | |

**索引**：index(kb_id), index(user_id)

---

## 5. t_chat_message（消息）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | 消息 ID |
| session_id | String | FK → t_chat_session.id, not null | 所属会话 |
| role | String(16) | not null | user / assistant（MessageRole 枚举） |
| content | Text | not null | 消息内容 |
| retrieval_context | JSONB | nullable | 关联的 RetrievalResult 摘要（引用的 chunk 列表） |
| trace_id | String(64) | nullable | 关联 trace_id（MVP 仅 trace_id，不关联 Span 树） |
| token_count | Integer | default 0 | |
| latency_ms | Integer | nullable | 端到端耗时 |
| created_at | DateTime | not null | |

**索引**：index(session_id), index(trace_id)

---

## 6. t_trace_span（链路追踪节点）— ★ 预留表

> **重要**：本表为预留表，MVP 阶段仅建表结构，**不写入任何 Span 数据**。
> MVP 仅实现 trace_id 透传 + X-Trace-Id 响应头 + 结构化日志。
> 复杂 Span 树 / @rag_trace_node / 可视化追踪留待 P7 生产特性阶段。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | Span ID |
| trace_id | String(64) | not null, indexed | 一次请求的 Trace ID |
| parent_id | String | nullable | 父 Span ID（树形，MVP 不用） |
| node_name | String(64) | not null | 节点名（parse/chunk/embed/retrieve/llm_stream/sse_push） |
| node_type | String(16) | not null | ingestion/retrieval/generation/transport |
| status | String(16) | default "running" | running/success/failed |
| input_summary | JSONB | nullable | 输入摘要（截断） |
| output_summary | JSONB | nullable | 输出摘要 |
| error_message | Text | nullable | |
| start_time | DateTime | not null | |
| end_time | DateTime | nullable | |
| duration_ms | Integer | nullable | |
| created_at | DateTime | not null | |

**索引**：index(trace_id), index(parent_id)

---

## 7. t_model_provider（模型供应商配置）

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | String | PK, snowflake | |
| name | String(64) | not null, unique | 供应商标识（qwen/openai/deepseek） |
| base_url | String(256) | not null | API 端点 |
| api_key_ref | String(128) | not null | 密钥引用名（实际密钥从环境变量读，不入库明文） |
| chat_model | String(64) | not null | 默认对话模型（如 qwen-plus） |
| embedding_model | String(64) | not null | 默认 Embedding 模型 |
| embedding_dim | Integer | not null | |
| enabled | Boolean | default true | |
| priority | Integer | default 0 | 路由优先级（MVP 单供应商，预留） |
| created_at | DateTime | not null | |
| updated_at | DateTime | not null | |

**索引**：unique(name)

---

## 8. 实体关系图

```
t_knowledge_base 1──* t_document 1──* t_document_chunk
        │
        └──* t_chat_session 1──* t_chat_message
                                      │
                                      └── trace_id（关联 t_trace_span.trace_id，MVP 不写）

t_model_provider 独立配置表，被 Embedding/LLM Client 引用

t_trace_span 预留表（MVP 不写入），通过 trace_id 与 t_chat_message 关联
```

---

## 9. 公共字段 mixin

所有表共享以下公共字段（通过 `persistence/models/base.py` 的 mixin 实现）：

| 字段 | 说明 |
|---|---|
| id | String，主键，雪花 ID（framework/core/snowflake.py 生成） |
| created_at | DateTime，创建时自动填充 |
| updated_at | DateTime，更新时自动填充 |

软删除字段 `deleted_at`（DateTime, nullable）按需添加，MVP 阶段暂不强制。
