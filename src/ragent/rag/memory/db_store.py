"""基于 PostgreSQL 的对话记忆实现。

DbMemoryStore 实现类才允许依赖 persistence.repositories（base 接口不依赖）。

MVP 仅实现 load_history + append_message。
summarize 不实现（返回 None），clear 预留。
"""

from __future__ import annotations

from ragent.domain.dto import ChatMessage
from ragent.framework.core.logging import get_logger
from ragent.persistence.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from ragent.rag.memory.base import BaseMemoryStore

_logger = get_logger(__name__)


class DbMemoryStore(BaseMemoryStore):
    """基于 PostgreSQL 的对话记忆。

    依赖 ChatMessageRepository + ChatSessionRepository 持久化消息与会话。
    """

    def __init__(
        self,
        *,
        chat_message_repo: ChatMessageRepository,
        chat_session_repo: ChatSessionRepository,
    ) -> None:
        """初始化 DbMemoryStore。

        Args:
            chat_message_repo: 消息 Repository
            chat_session_repo: 会话 Repository（用于 get_or_create）
        """
        self._message_repo = chat_message_repo
        self._session_repo = chat_session_repo

    async def load_history(
        self,
        session_id: str,
        max_messages: int,
    ) -> list[ChatMessage]:
        """加载最近 N 条对话历史。

        从 t_chat_message 取最近 max_messages 条，映射为 domain.dto.ChatMessage。

        Args:
            session_id: 会话 ID
            max_messages: 最多返回的消息数

        Returns:
            消息列表（按时间升序）
        """
        entities = await self._message_repo.list_recent(session_id, max_messages)
        messages = [
            ChatMessage(role=entity.role, content=entity.content)
            for entity in entities
        ]
        _logger.info(
            "memory_load_history",
            session_id=session_id,
            max_messages=max_messages,
            loaded=len(messages),
        )
        return messages

    async def append_message(
        self,
        session_id: str,
        message: ChatMessage,
    ) -> None:
        """追加一条消息到会话历史。

        同时确保会话存在（get_or_create）并更新消息计数。
        retrieval_context / trace_id 等持久化字段由调用方（ChatService）直接通过
        ChatMessageRepository.append_message 写入，本方法仅写入基础消息。

        Args:
            session_id: 会话 ID
            message: 待追加的消息（role/content）
        """
        # 确保会话存在
        await self._session_repo.get_or_create(session_id)
        # 写消息
        await self._message_repo.append_message(
            session_id,
            message,
        )
        # 更新消息计数
        await self._session_repo.increment_message_count(session_id, delta=1)
        _logger.info(
            "memory_append_message",
            session_id=session_id,
            role=message.role,
        )

    async def summarize(self, session_id: str) -> str | None:
        """摘要压缩（MVP 不实现，返回 None）。

        Args:
            session_id: 会话 ID

        Returns:
            None（MVP 不实现摘要压缩）
        """
        _logger.info("memory_summarize_not_implemented", session_id=session_id)
        return None

    async def clear(self, session_id: str) -> None:
        """清空会话历史（预留）。

        MVP 不强制实现，仅记录日志。

        Args:
            session_id: 会话 ID
        """
        _logger.info("memory_clear_not_implemented", session_id=session_id)


__all__ = ["DbMemoryStore"]
