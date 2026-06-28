"""T15 SSE 接口测试（api/v1/chat.py）。

约束：
- 通过 FastAPI TestClient / httpx ASGITransport 测试，不监听真实端口
- LLM / Retriever / Memory 全 Mock（不依赖真实服务）
- 覆盖：
  - POST /api/v1/chat/sse 返回 SSE 事件流
  - start 事件含 trace_id
  - delta 事件含 content
  - done 事件含 trace_id + finish_reason
  - error 事件含 trace_id（LLM 失败场景）
  - 客户端断开不崩溃
  - 请求体校验（缺字段返回 422）
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from ragent.domain.dto import ChatChunk, ChatMessage, RetrievalResult
from ragent.domain.enums import MessageRole
from ragent.domain.value_objects import ChatOptions, RetrievalQuery
from ragent.framework.core.exceptions import BizException
from ragent.infra_ai.rerank.identity import IdentityReranker
from ragent.main import create_app
from ragent.rag.prompt.service import PromptService
from ragent.rag.retrieve.postprocessor.dedup import DeduplicationPostProcessor
from ragent.service.chat_service import ChatService

# ---------- Mock 实现 ----------


class _MockRetriever:
    """Mock Retriever：返回预设结果。"""

    def __init__(self, results: list[RetrievalResult] | None = None) -> None:
        self._results = results or [
            RetrievalResult(
                chunk_id="chunk-1",
                document_id="doc-1",
                kb_id="kb-1",
                content="测试证据内容",
                score=0.9,
            ),
        ]

    async def retrieve(self, query: RetrievalQuery, top_k: int) -> list[RetrievalResult]:
        return list(self._results[:top_k])

    def channel_name(self) -> str:
        return "mock"


class _MockLLMClient:
    """Mock LLM：返回预设 chunk 流；可配置为抛异常。"""

    def __init__(
        self,
        chunks: list[ChatChunk] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self._chunks = chunks or [
            ChatChunk(delta="你好", finish_reason=None),
            ChatChunk(delta="，这是回答", finish_reason=None),
            ChatChunk(delta="", finish_reason="stop"),
        ]
        self._raise = raise_exc

    async def chat(self, messages: list[ChatMessage], options: ChatOptions) -> str:
        return "".join(c.delta for c in self._chunks if c.delta)

    def stream_chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[ChatChunk]:
        return self._stream()

    async def _stream(self) -> AsyncIterator[ChatChunk]:
        if self._raise is not None:
            raise self._raise
        for chunk in self._chunks:
            yield chunk

    def model_name(self) -> str:
        return "mock-llm"


class _MockMemoryStore:
    """Mock Memory：空历史。"""

    async def load_history(self, session_id: str, max_messages: int) -> list[ChatMessage]:
        return []

    async def append_message(self, session_id: str, message: ChatMessage) -> None:
        pass

    async def summarize(self, session_id: str) -> str | None:
        return None

    async def clear(self, session_id: str) -> None:
        pass


class _MockChatMessageRepo:
    """Mock ChatMessageRepository。"""

    def __init__(self) -> None:
        self.appended: list[dict[str, Any]] = []

    async def append_message(
        self,
        session_id: str,
        message: ChatMessage,
        *,
        retrieval_context: dict[str, Any] | None = None,
        trace_id: str | None = None,
        token_count: int = 0,
        latency_ms: int | None = None,
    ) -> Any:
        self.appended.append({
            "session_id": session_id,
            "role": message.role,
            "content": message.content,
            "retrieval_context": retrieval_context,
            "trace_id": trace_id,
        })
        return None


class _MockChatSessionRepo:
    """Mock ChatSessionRepository。"""

    async def get_or_create(
        self,
        session_id: str,
        *,
        kb_id: str | None = None,
        user_id: str | None = None,
    ) -> Any:
        return None

    async def increment_message_count(self, session_id: str, delta: int = 1) -> None:
        pass


# ---------- Fixture ----------


@pytest.fixture
async def sse_app_client(
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[tuple[httpx.AsyncClient, _MockChatMessageRepo]]:
    """构造 ASGI 测试客户端 + 注入全 Mock ChatService。

    Yields:
        (client, msg_repo) - msg_repo 用于验证消息持久化
    """
    msg_repo = _MockChatMessageRepo()

    def _override_chat_service() -> ChatService:
        return ChatService(
            retriever=_MockRetriever(),
            post_processors=[DeduplicationPostProcessor()],
            reranker=IdentityReranker(),
            llm_client=_MockLLMClient(),
            memory_store=_MockMemoryStore(),
            prompt_service=PromptService(),
            chat_message_repo=msg_repo,
            chat_session_repo=_MockChatSessionRepo(),
        )

    app = create_app()
    from ragent.api.deps import get_chat_service as _orig_get_chat_service

    app.dependency_overrides[_orig_get_chat_service] = _override_chat_service

    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        yield c, msg_repo

    app.dependency_overrides.clear()


def _parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    """解析 SSE 原始文本为事件列表。

    Args:
        raw_text: SSE 原始响应文本

    Returns:
        [{"event": "...", "data": {...}}, ...]
    """
    events: list[dict[str, Any]] = []
    current_event = ""
    current_data_lines: list[str] = []

    for line in raw_text.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data_lines.append(line[len("data:"):].strip())
        elif line == "":
            # 事件分隔
            if current_event and current_data_lines:
                data_str = "\n".join(current_data_lines)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {"raw": data_str}
                events.append({"event": current_event, "data": data})
            current_event = ""
            current_data_lines = []
    return events


# ---------- SSE 接口测试 ----------


@pytest.mark.asyncio
async def test_chat_sse_returns_event_stream(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """POST /api/v1/chat/sse 返回 SSE 事件流（start → delta* → done）。"""
    client, _ = sse_app_client
    payload = {
        "session_id": "sess-sse-1",
        "kb_id": "kb-1",
        "question": "测试问题",
        "top_k": 3,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    # 必须包含 start / delta / done
    assert "start" in event_types
    assert "delta" in event_types
    assert "done" in event_types
    # start 在最前
    assert event_types[0] == "start"
    # done 在最后
    assert event_types[-1] == "done"


@pytest.mark.asyncio
async def test_chat_sse_start_event_contains_trace_id(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """start 事件包含 trace_id。"""
    client, _ = sse_app_client
    payload = {
        "session_id": "sess-sse-2",
        "kb_id": "kb-1",
        "question": "q",
        "top_k": 1,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    events = _parse_sse_events(resp.text)
    start_event = events[0]

    assert start_event["event"] == "start"
    assert "trace_id" in start_event["data"]
    assert start_event["data"]["trace_id"]


@pytest.mark.asyncio
async def test_chat_sse_delta_contains_content(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """delta 事件包含 content。"""
    client, _ = sse_app_client
    payload = {
        "session_id": "sess-sse-3",
        "kb_id": "kb-1",
        "question": "q",
        "top_k": 1,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    events = _parse_sse_events(resp.text)
    delta_events = [e for e in events if e["event"] == "delta"]

    assert len(delta_events) >= 1
    for d in delta_events:
        assert "content" in d["data"]
    # 拼接后应包含 Mock LLM 的输出
    full_content = "".join(d["data"]["content"] for d in delta_events)
    assert "你好" in full_content


@pytest.mark.asyncio
async def test_chat_sse_done_event_contains_trace_id(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """done 事件包含 trace_id + finish_reason。"""
    client, _ = sse_app_client
    payload = {
        "session_id": "sess-sse-4",
        "kb_id": "kb-1",
        "question": "q",
        "top_k": 1,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    events = _parse_sse_events(resp.text)
    done_event = events[-1]

    assert done_event["event"] == "done"
    assert "trace_id" in done_event["data"]
    assert "finish_reason" in done_event["data"]


@pytest.mark.asyncio
async def test_chat_sse_persists_messages(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """SSE 完成后，user + assistant 消息已持久化。"""
    client, msg_repo = sse_app_client
    payload = {
        "session_id": "sess-persist",
        "kb_id": "kb-1",
        "question": "持久化测试",
        "top_k": 1,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    assert resp.status_code == 200

    # user 消息
    user_msgs = [m for m in msg_repo.appended if m["role"] == MessageRole.USER.value]
    assert len(user_msgs) == 1
    assert user_msgs[0]["content"] == "持久化测试"

    # assistant 消息
    assistant_msgs = [m for m in msg_repo.appended if m["role"] == MessageRole.ASSISTANT.value]
    assert len(assistant_msgs) == 1
    assert assistant_msgs[0]["content"]
    # retrieval_context 非空
    assert assistant_msgs[0]["retrieval_context"] is not None
    assert len(assistant_msgs[0]["retrieval_context"]["chunk_ids"]) >= 1


@pytest.mark.asyncio
async def test_chat_sse_request_validation_missing_field() -> None:
    """请求体缺字段返回 422。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        # 缺 question
        payload = {"session_id": "s", "kb_id": "k"}
        resp = await c.post("/api/v1/chat/sse", json=payload)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_sse_request_validation_invalid_top_k() -> None:
    """top_k <= 0 返回 422。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        payload = {
            "session_id": "s",
            "kb_id": "k",
            "question": "q",
            "top_k": 0,
        }
        resp = await c.post("/api/v1/chat/sse", json=payload)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_sse_trace_id_in_response_header(
    sse_app_client: tuple[httpx.AsyncClient, _MockChatMessageRepo],
) -> None:
    """响应头含 X-Trace-Id。"""
    client, _ = sse_app_client
    payload = {
        "session_id": "sess-header",
        "kb_id": "kb-1",
        "question": "q",
        "top_k": 1,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    assert resp.status_code == 200
    assert resp.headers.get("x-trace-id")


@pytest.mark.asyncio
async def test_chat_sse_error_event_contains_trace_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """LLM 失败时，error 事件含 trace_id。"""
    msg_repo = _MockChatMessageRepo()

    def _override_chat_service_error() -> ChatService:
        return ChatService(
            retriever=_MockRetriever(),
            post_processors=[DeduplicationPostProcessor()],
            reranker=IdentityReranker(),
            llm_client=_MockLLMClient(raise_exc=BizException(message="LLM 调用失败", code=30030)),
            memory_store=_MockMemoryStore(),
            prompt_service=PromptService(),
            chat_message_repo=msg_repo,
            chat_session_repo=_MockChatSessionRepo(),
        )

    app = create_app()
    from ragent.api.deps import get_chat_service as _orig_get_chat_service

    app.dependency_overrides[_orig_get_chat_service] = _override_chat_service_error

    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        payload = {
            "session_id": "sess-err",
            "kb_id": "kb-1",
            "question": "q",
            "top_k": 1,
        }
        resp = await c.post("/api/v1/chat/sse", json=payload)
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        error_events = [e for e in events if e["event"] == "error"]
        assert len(error_events) == 1
        err_data = error_events[0]["data"]
        assert "trace_id" in err_data
        assert err_data["trace_id"]
        assert err_data["code"] == 30030

    app.dependency_overrides.clear()
