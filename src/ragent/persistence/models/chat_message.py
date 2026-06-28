"""t_chat_message 消息表 ORM Model。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ragent.persistence.models.base import Base, TimestampMixin


class ChatMessage(Base, TimestampMixin):
    """对话消息。"""

    __tablename__ = "t_chat_message"

    session_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("t_chat_session.id"), nullable=False, index=True, comment="所属会话"
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色：user/assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    retrieval_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="关联的检索结果摘要")
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="关联 trace_id")
    token_count: Mapped[int] = mapped_column(Integer, default=0, comment="token 数")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="端到端耗时(ms)")
