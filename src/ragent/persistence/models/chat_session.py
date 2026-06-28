"""t_chat_session 会话表 ORM Model。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ragent.persistence.models.base import Base, TimestampMixin


class ChatSession(Base, TimestampMixin):
    """对话会话。"""

    __tablename__ = "t_chat_session"

    title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="会话标题（MVP 可空）")
    kb_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("t_knowledge_base.id"),
        nullable=True,
        index=True,
        comment="关联知识库",
    )
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="用户 ID（预留）")
    message_count: Mapped[int] = mapped_column(Integer, default=0, comment="消息数")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", comment="状态：active/archived")
