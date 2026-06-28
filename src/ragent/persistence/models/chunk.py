"""t_document_chunk 文档分块表 ORM Model。

注意：向量本身不入 PostgreSQL，存于 Milvus，以 chunk.id 关联。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ragent.domain.enums import ChunkEmbeddingStatus
from ragent.persistence.models.base import Base, TimestampMixin


class DocumentChunk(Base, TimestampMixin):
    """文档分块。"""

    __tablename__ = "t_document_chunk"

    document_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("t_document.id"), nullable=False, index=True, comment="所属文档"
    )
    kb_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("t_knowledge_base.id"),
        nullable=False,
        index=True,
        comment="所属知识库（冗余，便于按 KB 检索）",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="分块文本")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="文档内序号")
    token_count: Mapped[int] = mapped_column(Integer, default=0, comment="该块 token 数")
    char_count: Mapped[int] = mapped_column(Integer, default=0, comment="字符数")
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, default=dict, comment="来源页码/章节/标题等结构化信息"
    )
    embedding_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ChunkEmbeddingStatus.PENDING.value,
        index=True,
        comment="Embedding 状态",
    )
