"""t_document 文档表 ORM Model。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ragent.domain.enums import DocumentStatus
from ragent.persistence.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """文档。"""

    __tablename__ = "t_document"

    kb_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("t_knowledge_base.id"), nullable=False, index=True, comment="所属知识库"
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False, comment="文件名")
    file_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="文件类型")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="字节数")
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="SHA256，用于去重/幂等")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=DocumentStatus.PENDING.value,
        index=True,
        comment="文档状态",
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, comment="分块数")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, comment="估算 token 数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
