"""跨层共享值对象（dataclass）。

纯领域，零业务依赖。供 persistence / service / schemas / infra_ai / rag / ingestion 共享。

注意：
- ChatMessage 为领域消息结构，与 persistence/models/chat_message.py 的 ORM Model 严格区分。
- VectorRecord.id 与 t_document_chunk.id 一致，向量本身不入 PostgreSQL，存于 Milvus。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Section:
    """章节/分页结构。

    Attributes:
        content: 该章节的文本内容
        page: 页码（PDF 文档有效，TXT/MD 为 None）
        heading: 章节标题（Markdown 文档有效，TXT/PDF 为 None）
    """

    content: str
    page: int | None = None
    heading: str | None = None


@dataclass
class ParsedDocument:
    """解析后的文档。

    Attributes:
        text: 全文文本（合并所有 section 后的纯文本）
        sections: 章节/分页结构（保留页码、标题等元信息）
        metadata: 文档级元信息（标题、作者、页数、文件类型等）
    """

    text: str
    sections: list[Section] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkDraft:
    """分块草稿（分块器输出，未持久化）。

    Attributes:
        content: 分块文本
        chunk_index: 文档内序号（从 0 开始）
        metadata: 来源页码/章节/标题等结构化信息
    """

    content: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorRecord:
    """向量记录（向量库写入单元）。

    Attributes:
        id: 与 t_document_chunk.id 一致，作为 Milvus 主键
        vector: 浮点向量
        content: 原始文本（便于检索后取回）
        metadata: 结构化元信息（kb_id/document_id/page 等）
    """

    id: str
    vector: list[float]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    """向量检索命中结果。

    Attributes:
        id: chunk.id
        score: 相似度分数（距离越小越相似，由实现负责归一化方向）
        content: 命中分块的原始文本
        metadata: 结构化元信息
    """

    id: str
    score: float
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """检索结果（统一抽象，第三批使用）。

    Attributes:
        chunk_id: 命中的 chunk.id
        document_id: 所属文档
        kb_id: 所属知识库
        content: 命中分块的文本
        score: 检索分数
        metadata: 元信息
        retrieval_channel: 检索通道标识（MVP: "vector_default"）
        rerank_score: Rerank 后分数（MVP: None）
    """

    chunk_id: str
    document_id: str
    kb_id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    retrieval_channel: str = "vector_default"
    rerank_score: float | None = None


@dataclass
class ChatChunk:
    """LLM 流式输出 chunk（第三批使用）。

    Attributes:
        delta: 增量内容
        finish_reason: 结束原因（stop/length 等），非结束 chunk 为 None
    """

    delta: str
    finish_reason: str | None = None


@dataclass
class ChatMessage:
    """领域消息结构（非 ORM）。

    注意：与 persistence/models/chat_message.py 的 ORM Model 严格区分。
    本类仅用于领域层 / service 层 / Memory 层传递消息结构。

    Attributes:
        role: 消息角色（user/assistant，对应 MessageRole 枚举）
        content: 消息内容
    """

    role: str
    content: str


__all__ = [
    "ChatChunk",
    "ChatMessage",
    "ChunkDraft",
    "ParsedDocument",
    "RetrievalResult",
    "Section",
    "VectorHit",
    "VectorRecord",
]
