"""T14 MemoryStore 单元测试。

约束：
- 不依赖真实 DB，Mock Repository
- 覆盖：
  - DbMemoryStore.load_history 返回 domain.dto.ChatMessage 列表
  - DbMemoryStore.append_message 调用 repo 写入
  - DbMemoryStore.summarize 返回 None（MVP 未实现）
  - DbMemoryStore.clear 仅记录日志（MVP 预留）
  - BaseMemoryStore 协议符合性
"""

from __future__ import annotations

from typing import Any

import pytest

from ragent.domain.dto import ChatMessage
from ragent.domain.enums import MessageRole
from ragent.rag.memory.base import BaseMemoryStore
from ragent.rag.memory.db_store import DbMemoryStore

# ---------- Mock Repositories ----------


class _MockMessageEntity:
    """Mock ChatMessage ORM 实体。"""

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


class _MockChatMessageRepo:
    """Mock ChatMessageRepository。"""

    def __init__(self, recent_messages: list[_MockMessageEntity] | None = None) -> None:
        self._recent = recent_messages or []
        self.appended: list[tuple[str, ChatMessage, dict[str, Any]]] = []

    async def list_recent(
        self,
        session_id: str,
        max_messages: int,
    ) -> list[_MockMessageEntity]:
        return list(self._recent[:max_messages])

    async def append_message(
        self,
        session_id: str,
        message: ChatMessage,
        *,
        retrieval_context: dict[str, Any] | None = None,
        trace_id: str | None = None,
        token_count: int = 0,
        latency_ms: int | None = None,
    ) -> _MockMessageEntity:
        self.appended.append(
            (
                session_id,
                message,
                {
                    "retrieval_context": retrieval_context,
                    "trace_id": trace_id,
                    "token_count": token_count,
                    "latency_ms": latency_ms,
                },
            )
        )
        return _MockMessageEntity(message.role, message.content)


class _MockChatSessionRepo:
    """Mock ChatSessionRepository。"""

    def __init__(self) -> None:
        self.get_or_create_calls: list[tuple[str, str | None]] = []
        self.increment_calls: list[tuple[str, int]] = []

    async def get_or_create(
        self,
        session_id: str,
        *,
        kb_id: str | None = None,
        user_id: str | None = None,
    ) -> Any:
        self.get_or_create_calls.append((session_id, kb_id))
        return None

    async def increment_message_count(self, session_id: str, delta: int = 1) -> None:
        self.increment_calls.append((session_id, delta))


# ---------- 协议符合性 ----------


def test_db_memory_store_implements_base_protocol() -> None:
    """DbMemoryStore 符合 BaseMemoryStore 协议。"""
    store = DbMemoryStore(
        chat_message_repo=_MockChatMessageRepo(),
        chat_session_repo=_MockChatSessionRepo(),
    )
    assert isinstance(store, BaseMemoryStore)


# ---------- load_history ----------


@pytest.mark.asyncio
async def test_load_history_returns_domain_messages() -> None:
    """load_history 把 ORM 实体映射为 domain.dto.ChatMessage。"""
    entities = [
        _MockMessageEntity(MessageRole.USER.value, "你好"),
        _MockMessageEntity(MessageRole.ASSISTANT.value, "你好，有什么可以帮您？"),
    ]
    msg_repo = _MockChatMessageRepo(entities)
    session_repo = _MockChatSessionRepo()
    store = DbMemoryStore(
        chat_message_repo=msg_repo,
        chat_session_repo=session_repo,
    )

    messages = await store.load_history("sess-1", 10)

    assert len(messages) == 2
    assert all(isinstance(m, ChatMessage) for m in messages)
    assert messages[0].role == MessageRole.USER.value
    assert messages[0].content == "你好"
    assert messages[1].role == MessageRole.ASSISTANT.value
    assert messages[1].content == "你好，有什么可以帮您？"


@pytest.mark.asyncio
async def test_load_history_empty() -> None:
    """无历史返回空列表。"""
    msg_repo = _MockChatMessageRepo([])
    store = DbMemoryStore(
        chat_message_repo=msg_repo,
        chat_session_repo=_MockChatSessionRepo(),
    )

    messages = await store.load_history("empty-sess", 10)
    assert messages == []


@pytest.mark.asyncio
async def test_load_history_respects_max_messages() -> None:
    """max_messages 限制返回条数。"""
    entities = [_MockMessageEntity("user", f"msg-{i}") for i in range(5)]
    msg_repo = _MockChatMessageRepo(entities)
    store = DbMemoryStore(
        chat_message_repo=msg_repo,
        chat_session_repo=_MockChatSessionRepo(),
    )

    messages = await store.load_history("sess", 3)
    assert len(messages) == 3


# ---------- append_message ----------


@pytest.mark.asyncio
async def test_append_message_calls_repo() -> None:
    """append_message 调用 message_repo.append_message 与 session_repo。"""
    msg_repo = _MockChatMessageRepo()
    session_repo = _MockChatSessionRepo()
    store = DbMemoryStore(
        chat_message_repo=msg_repo,
        chat_session_repo=session_repo,
    )

    msg = ChatMessage(role=MessageRole.USER.value, content="测试消息")
    await store.append_message("sess-1", msg)

    # 验证 message_repo 被调用
    assert len(msg_repo.appended) == 1
    appended_session, appended_msg, _ = msg_repo.appended[0]
    assert appended_session == "sess-1"
    assert appended_msg.role == MessageRole.USER.value
    assert appended_msg.content == "测试消息"
    # 验证 session_repo.get_or_create 被调用
    assert any(call[0] == "sess-1" for call in session_repo.get_or_create_calls)
    # 验证 increment_message_count 被调用（+1）
    assert ("sess-1", 1) in session_repo.increment_calls


@pytest.mark.asyncio
async def test_append_message_assistant_role() -> None:
    """append_message 支持 assistant 角色。"""
    msg_repo = _MockChatMessageRepo()
    store = DbMemoryStore(
        chat_message_repo=msg_repo,
        chat_session_repo=_MockChatSessionRepo(),
    )

    msg = ChatMessage(role=MessageRole.ASSISTANT.value, content="回复内容")
    await store.append_message("sess-2", msg)

    assert len(msg_repo.appended) == 1
    assert msg_repo.appended[0][1].role == MessageRole.ASSISTANT.value


# ---------- summarize (MVP 未实现) ----------


@pytest.mark.asyncio
async def test_summarize_returns_none() -> None:
    """summarize MVP 不实现，返回 None。"""
    store = DbMemoryStore(
        chat_message_repo=_MockChatMessageRepo(),
        chat_session_repo=_MockChatSessionRepo(),
    )

    result = await store.summarize("sess-1")
    assert result is None


# ---------- clear (MVP 预留) ----------


@pytest.mark.asyncio
async def test_clear_does_not_raise() -> None:
    """clear MVP 预留，仅记录日志，不抛异常。"""
    store = DbMemoryStore(
        chat_message_repo=_MockChatMessageRepo(),
        chat_session_repo=_MockChatSessionRepo(),
    )

    # 不抛异常即可
    await store.clear("sess-1")
