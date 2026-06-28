"""对话记忆抽象接口。

BaseMemoryStore 只依赖 domain.dto.ChatMessage，
禁止依赖 persistence / api（重点约束）。
实现类（DbMemoryStore）才允许依赖 persistence.repositories。

MVP 仅实现 load_history + append_message。
summarize 不实现（返回 None），clear 预留。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import ChatMessage


@runtime_checkable
class BaseMemoryStore(Protocol):
    """对话记忆抽象接口。

    实现类需提供：
    - load_history: 加载最近 N 条对话历史
    - append_message: 追加一条消息
    - summarize: 摘要压缩（MVP 不实现，返回 None）
    - clear: 清空会话历史（预留）

    MVP 约束：
    - 仅实现 load_history + append_message
    - summarize 返回 None（不实现摘要压缩）
    """

    async def load_history(
        self,
        session_id: str,
        max_messages: int,
    ) -> list[ChatMessage]:
        """加载最近 N 条对话历史。

        Args:
            session_id: 会话 ID
            max_messages: 最多返回的消息数

        Returns:
            消息列表（按时间升序，即最旧的在前）
        """
        ...

    async def append_message(
        self,
        session_id: str,
        message: ChatMessage,
    ) -> None:
        """追加一条消息到会话历史。

        Args:
            session_id: 会话 ID
            message: 待追加的消息（role/content）
        """
        ...

    async def summarize(self, session_id: str) -> str | None:
        """摘要压缩（MVP 不实现，返回 None）。

        Args:
            session_id: 会话 ID

        Returns:
            None（MVP 不实现摘要）
        """
        ...

    async def clear(self, session_id: str) -> None:
        """清空会话历史（预留）。

        Args:
            session_id: 会话 ID
        """
        ...


__all__ = ["BaseMemoryStore"]
