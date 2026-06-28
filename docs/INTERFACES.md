# INTERFACES.md

> Ragent-Py 核心抽象接口归属与契约
>
> 原则：**base 接口只依赖 domain，禁止依赖 persistence。**
> 实现类才允许依赖 persistence / infra_ai 具体实现。

---

## 1. 接口归属与依赖总表

| 接口 | 位置 | 允许依赖 | 禁止依赖 |
|---|---|---|---|
| BaseDocumentParser | `ingestion/parser/base.py` | `domain.dto.ParsedDocument` | persistence / infra_ai / rag / api |
| BaseChunker | `ingestion/chunker/base.py` | `domain.dto.ChunkDraft` / `domain.value_objects.ChunkConfig` | persistence / infra_ai / rag / api |
| BaseEmbeddingClient | `infra_ai/embedding/base.py` | `domain` | persistence / rag / ingestion / api |
| BaseVectorStore | `rag/vector/base.py` | `domain.dto.VectorRecord` / `domain.dto.VectorHit` | **persistence** / api |
| BaseRetriever | `rag/retrieve/base.py` | `domain.dto.RetrievalResult` / `domain.value_objects.RetrievalQuery` | **persistence** / api |
| BasePostProcessor | `rag/retrieve/postprocessor/base.py` | `domain.dto.RetrievalResult` | **persistence** / api |
| BaseReranker | `infra_ai/rerank/base.py` | `domain.dto.RetrievalResult` | persistence / api |
| BaseLLMClient | `infra_ai/llm/base.py` | `domain.dto.ChatChunk` / `domain.value_objects.ChatOptions` | persistence / rag / api |
| BaseMemoryStore | `rag/memory/base.py` | `domain.dto` / `domain.value_objects` | **persistence**（重点） / api |

> **重点**：BaseMemoryStore / BaseVectorStore / BaseRetriever / BasePostProcessor 的 base 接口**不得 import persistence**。实现类（如 `db_store.py` / `milvus.py` / `vector_retriever.py`）才允许依赖 persistence。

---

## 2. BaseDocumentParser

**位置**：`ingestion/parser/base.py`

**职责**：将文件解析为结构化文本（含分页/章节元信息）。

### 方法契约

```python
class BaseDocumentParser(Protocol):
    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """将文件解析为结构化文档"""
        ...

    def supported_types(self) -> list[str]:
        """声明支持的文件类型"""
        ...
```

### ParsedDocument（domain/dto.py）

```python
@dataclass
class ParsedDocument:
    text: str                    # 全文文本
    sections: list[Section]      # 章节/分页结构
    metadata: dict               # 文档级元信息（标题、作者、页数等）

@dataclass
class Section:
    content: str
    page: int | None             # 页码（PDF）
    heading: str | None          # 章节标题
```

### 实现类
- `ingestion/parser/txt.py` → TxtParser
- `ingestion/parser/markdown.py` → MarkdownParser
- `ingestion/parser/pdf.py` → PdfParser（保留页码元信息）
- `ingestion/parser/registry.py` → ParserRegistry（按 file_type 路由）

### MVP 支持类型
- TXT / Markdown / PDF（PPT/HTML/unstructured 暂缓）

---

## 3. BaseChunker

**位置**：`ingestion/chunker/base.py`

**职责**：将解析结果切分为分块草稿。

### 方法契约

```python
class BaseChunker(Protocol):
    async def chunk(self, parsed: ParsedDocument, config: ChunkConfig) -> list[ChunkDraft]:
        """将解析文档切分为分块草稿"""
        ...

    def name(self) -> str:
        """策略标识（fixed/sentence/recursive）"""
        ...
```

### ChunkConfig（domain/value_objects.py）

```python
@dataclass
class ChunkConfig:
    chunk_size: int              # 分块大小（字符数）
    overlap: int                 # 重叠字符数
    separators: list[str]        # 分隔符优先级（recursive 用）
```

### ChunkDraft（domain/dto.py）

```python
@dataclass
class ChunkDraft:
    content: str
    chunk_index: int
    metadata: dict               # 来源页码/章节等
```

### 实现类
- `ingestion/chunker/fixed.py` → FixedSizeChunker
- `ingestion/chunker/sentence.py` → SentenceChunker
- `ingestion/chunker/recursive.py` → RecursiveChunker（默认）

---

## 4. BaseEmbeddingClient

**位置**：`infra_ai/embedding/base.py`

**职责**：文本向量化。

### 方法契约

```python
class BaseEmbeddingClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化"""
        ...

    async def embed_one(self, text: str) -> list[float]:
        """单条向量化（便捷方法）"""
        ...

    def dim(self) -> int:
        """向量维度"""
        ...

    def model_name(self) -> str:
        """模型标识"""
        ...
```

### 实现类
- `infra_ai/embedding/openai_compat.py` → OpenAICompatibleEmbeddingClient（httpx async）
- `infra_ai/factory.py` → 按 ModelProvider 配置构建客户端

### 约束
- 批量请求支持
- 可 Mock（便于 CI）

---

## 5. BaseVectorStore

**位置**：`rag/vector/base.py`

**职责**：向量库抽象（仅实现类依赖 Milvus）。

### 方法契约

```python
class BaseVectorStore(Protocol):
    async def ensure_collection(self, collection_name: str, dim: int) -> None:
        """确保 collection 存在（幂等创建）"""
        ...

    async def upsert(self, collection_name: str, vectors: list[VectorRecord]) -> int:
        """批量写入/更新，返回写入数量"""
        ...

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filter_expr: str | None = None,
    ) -> list[VectorHit]:
        """向量近邻检索"""
        ...

    async def delete_by_document(self, collection_name: str, document_id: str) -> int:
        """按文档删除（文档下架场景）"""
        ...

    async def drop_collection(self, collection_name: str) -> None:
        """删除 collection"""
        ...
```

### VectorRecord / VectorHit（domain/dto.py）

```python
@dataclass
class VectorRecord:
    id: str                      # 与 t_document_chunk.id 一致
    vector: list[float]
    content: str
    metadata: dict

@dataclass
class VectorHit:
    id: str
    score: float
    content: str
    metadata: dict
```

### 实现类
- `rag/vector/milvus.py` → MilvusVectorStore（pymilvus async）

### 约束
- **base 接口禁止依赖 persistence**
- 后续可扩展 PgvectorVectorStore / QdrantVectorStore

---

## 6. BaseRetriever

**位置**：`rag/retrieve/base.py`

**职责**：执行检索，返回统一 RetrievalResult。

### 方法契约

```python
class BaseRetriever(Protocol):
    async def retrieve(self, query: RetrievalQuery, top_k: int) -> list[RetrievalResult]:
        """执行检索"""
        ...

    def channel_name(self) -> str:
        """通道标识（MVP: "vector_default"）"""
        ...
```

### RetrievalQuery（domain/value_objects.py）

```python
@dataclass
class RetrievalQuery:
    text: str
    kb_id: str | None
    session_id: str | None
```

### RetrievalResult（domain/dto.py）

```python
@dataclass
class RetrievalResult:
    chunk_id: str
    document_id: str
    kb_id: str
    content: str
    score: float
    metadata: dict
    retrieval_channel: str       # MVP: "vector_default"
    rerank_score: float | None   # MVP: None
```

### 实现类
- `rag/retrieve/vector_retriever.py` → VectorRetriever（调用 BaseEmbeddingClient + BaseVectorStore）

### 后续扩展
- IntentDirectedRetriever / VectorGlobalRetriever（多通道并行，P4 阶段）

---

## 7. BasePostProcessor

**位置**：`rag/retrieve/postprocessor/base.py`

**职责**：检索后处理链节点。

### 方法契约

```python
class BasePostProcessor(Protocol):
    async def process(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """对检索结果进行后处理"""
        ...

    def order(self) -> int:
        """链中执行顺序（小先执行）"""
        ...
```

### 实现类
- `rag/retrieve/postprocessor/dedup.py` → DeduplicationPostProcessor（按 chunk_id 去重，保留最高分，order=1）

### 约束
- **base 接口禁止依赖 persistence**
- 后续可扩展 RerankPostProcessor（P4）

---

## 8. BaseReranker

**位置**：`infra_ai/rerank/base.py`

**职责**：对候选结果重排序。

### 方法契约

```python
class BaseReranker(Protocol):
    async def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """对候选结果重排序"""
        ...

    def enabled(self) -> bool:
        """是否启用"""
        ...
```

### 实现类
- `infra_ai/rerank/identity.py` → IdentityReranker（MVP 默认，不排序直接返回，enabled=True 但直通）

### MVP 约束
- 仅 IdentityReranker，**暂缓** Rerank 模型调用

---

## 9. BaseLLMClient

**位置**：`infra_ai/llm/base.py`

**职责**：LLM 对话（流式 + 非流式）。

### 方法契约

```python
class BaseLLMClient(Protocol):
    async def chat(self, messages: list[ChatMessage], options: ChatOptions) -> str:
        """非流式对话"""
        ...

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[ChatChunk]:
        """流式对话（核心）"""
        ...

    def model_name(self) -> str:
        """模型标识"""
        ...
```

### ChatOptions（domain/value_objects.py）

```python
@dataclass
class ChatOptions:
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int | None = None
    stop: list[str] | None = None
```

### ChatChunk（domain/dto.py）

```python
@dataclass
class ChatChunk:
    delta: str                   # 增量内容
    finish_reason: str | None    # 结束原因（stop/length 等）
```

> 注：`ChatMessage` 此处指领域消息结构（role + content），与 `persistence/models/chat_message.py` 的 ORM Model 区分。

### 实现类
- `infra_ai/llm/openai_compat.py` → OpenAICompatibleLLMClient（httpx async + SSE 解析 + 首包探测）

### 约束
- stream_chat 返回 AsyncIterator[ChatChunk]
- 首包事件可探测（用于 SSE start 事件）
- 可 Mock（便于 CI）

---

## 10. BaseMemoryStore

**位置**：`rag/memory/base.py`

**职责**：对话记忆存储。

### 方法契约

```python
class BaseMemoryStore(Protocol):
    async def load_history(self, session_id: str, max_messages: int) -> list[ChatMessage]:
        """加载会话历史"""
        ...

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        """追加消息"""
        ...

    async def summarize(self, session_id: str) -> str | None:
        """摘要压缩（MVP 不实现，返回 None）"""
        ...

    async def clear(self, session_id: str) -> None:
        """清空"""
        ...
```

### 实现类
- `rag/memory/db_store.py` → DbMemoryStore（依赖 `persistence.repositories`）

### MVP 约束
- 仅实现 `load_history` + `append_message`
- `summarize` 返回 None（不实现摘要压缩，留待 P6）
- **base 接口禁止依赖 persistence**，实现类才依赖

### 依赖关系示意

```
rag/memory/base.py          (BaseMemoryStore)  ──► domain.dto / domain.value_objects
                                                ✗ persistence（禁止）

rag/memory/db_store.py      (DbMemoryStore)    ──► domain + persistence.repositories
```

---

## 11. domain 共享值对象汇总

为便于查阅，以下为 `domain/dto.py` 与 `domain/value_objects.py` 的完整内容：

### domain/dto.py
- ParsedDocument（text, sections, metadata）
- Section（content, page, heading）
- ChunkDraft（content, chunk_index, metadata）
- VectorRecord（id, vector, content, metadata）
- VectorHit（id, score, content, metadata）
- RetrievalResult（chunk_id, document_id, kb_id, content, score, metadata, retrieval_channel, rerank_score）
- ChatChunk（delta, finish_reason）
- ChatMessage（role, content）（领域消息结构，非 ORM）

### domain/value_objects.py
- ChunkConfig（chunk_size, overlap, separators）
- ChatOptions（temperature, top_p, max_tokens, stop）
- RetrievalQuery（text, kb_id, session_id）

### domain/enums.py
- DocumentStatus（pending/parsing/chunking/embedding/indexing/completed/failed）
- ChunkEmbeddingStatus（pending/embedded/indexed/failed）
- MessageRole（user/assistant）
- ProviderType（qwen/openai/deepseek）
- KnowledgeBaseStatus（active/archived）
