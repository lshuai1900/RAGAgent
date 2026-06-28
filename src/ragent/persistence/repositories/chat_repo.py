"""对话会话与消息 Repository。

依赖 domain（用枚举）+ persistence.models（用 ORM Model）+ BaseRepository。
service 层通过本 Repository 访问 t_chat_session / t_chat_message 表。

注意：
- ChatMessage ORM Model 与 domain.dto.ChatMessage 严格区分（前者含 retrieval_context 等持久化字段）
- Repository 负责 ORM 与领域结构之间的转换
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.domain.dto import ChatMessage as DomainChatMessage
from ragent.persistence.models.chat_message import ChatMessage
from ragent.persistence.models.chat_session import ChatSession
from ragent.persistence.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    """对话会话 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatSession)

    async def get_by_id(self, id: str) -> ChatSession | None:
        """按主键查询会话。"""
        return await self._session.get(ChatSession, id)

    async def get_or_create(
        self,
        session_id: str,
        *,
        kb_id: str | None = None,
        user_id: str | None = None,
    ) -> ChatSession:
        """按 ID 查询会话，不存在则创建。

        Args:
            session_id: 会话 ID
            kb_id: 关联知识库 ID（创建时设置）
            user_id: 用户 ID（创建时设置）

        Returns:
            会话实体
        """
        existing = await self._session.get(ChatSession, session_id)
        if existing is not None:
            return existing
        new_session = ChatSession(
            id=session_id,
            kb_id=kb_id,
            user_id=user_id,
            message_count=0,
            status="active",
        )
        self._session.add(new_session)
        await self._session.flush()
        return new_session

    async def increment_message_count(self, session_id: str, delta: int = 1) -> None:
        """更新会话消息计数。

        Args:
            session_id: 会话 ID
            delta: 增量
        """
        s = await self._session.get(ChatSession, session_id)
        if s is not None:
            s.message_count = max(0, s.message_count + delta)
            await self._session.flush()


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """对话消息 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatMessage)

    async def append_message(
        self,
        session_id: str,
        message: DomainChatMessage,
        *,
        retrieval_context: dict[str, Any] | None = None,
        trace_id: str | None = None,
        token_count: int = 0,
        latency_ms: int | None = None,
    ) -> ChatMessage:
        """追加一条消息（自动写入 session_id 与 role）。

        Args:
            session_id: 会话 ID
            message: 领域消息结构（role/content）
            retrieval_context: 检索上下文摘要（仅 assistant 消息携带）
            trace_id: 关联 trace_id
            token_count: token 数
            latency_ms: 端到端耗时（ms）

        Returns:
            已 flush 的 ChatMessage 实体（含生成的 id）
        """
        entity = ChatMessage(
            session_id=session_id,
            role=message.role,
            content=message.content,
            retrieval_context=retrieval_context,
            trace_id=trace_id,
            token_count=token_count,
            latency_ms=latency_ms,
        )
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_recent(
        self,
        session_id: str,
        max_messages: int,
    ) -> list[ChatMessage]:
        """列出会话最近的 N 条消息（按时间升序返回，最旧的在前）。

        Args:
            session_id: 会话 ID
            max_messages: 最多返回的消息数

        Returns:
            消息列表（按 created_at 升序）
        """
        if max_messages <= 0:
            return []
        # 先取最近 N 条（降序），再反转为升序
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(max_messages)
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def list_by_session(
        self,
        session_id: str,
        *,
        role: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """按会话列出消息（可按角色过滤）。

        Args:
            session_id: 会话 ID
            role: 可选角色过滤（user/assistant）
            limit: 每页大小
            offset: 偏移量

        Returns:
            消息列表（按 created_at 升序）
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if role is not None:
            stmt = stmt.where(ChatMessage.role == role)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_session(self, session_id: str) -> int:
        """统计会话消息数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session_id)
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)


__all__ = [
    "ChatMessageRepository",
    "ChatSessionRepository",
]
