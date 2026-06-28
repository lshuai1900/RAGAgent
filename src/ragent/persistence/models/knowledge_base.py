"""t_knowledge_base 知识库表 ORM Model。"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ragent.domain.enums import KnowledgeBaseStatus
from ragent.persistence.models.base import Base, TimestampMixin


class KnowledgeBase(Base, TimestampMixin):
    """知识库。"""

    __tablename__ = "t_knowledge_base"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, comment="名称")
    description: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="描述")
    collection_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Milvus collection 名")
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, default=1024, comment="向量维度")
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, comment="Embedding 模型标识")
    chunk_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="recursive", comment="分块策略")
    chunk_size: Mapped[int] = mapped_column(Integer, default=512, comment="分块大小")
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=64, comment="分块重叠")
    document_count: Mapped[int] = mapped_column(Integer, default=0, comment="文档数（冗余计数）")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=KnowledgeBaseStatus.ACTIVE.value,
        comment="状态：active/archived",
    )
