"""T15 SSE emitter 单元测试。

约束：
- 不依赖真实 HTTP，直接测试 emitter 函数
- 覆盖：
  - build_start_payload / build_delta_payload / build_done_payload / build_error_payload
  - serialize_event 格式
  - stream_sse_events 正常流程（start → delta* → done）
  - stream_sse_events 异常流程（RagentException → error 事件）
  - stream_sse_events 未知异常 → error 事件
  - stream_sse_events 客户端断开（CancelledError）不抛异常
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from ragent.domain.dto import ChatChunk
from ragent.framework.core.exceptions import BizException
from ragent.framework.sse.emitter import (
    EVENT_DELTA,
    EVENT_DONE,
    EVENT_ERROR,
    EVENT_START,
    build_delta_payload,
    build_done_payload,
    build_error_payload,
    build_start_payload,
    serialize_event,
    stream_sse_events,
)

# ---------- payload 构造 ----------


def test_build_start_payload_with_trace_id() -> None:
    """build_start_payload 含 trace_id。"""
    payload = build_start_payload("trace-123")
    assert payload == {"trace_id": "trace-123"}


def test_build_delta_payload() -> None:
    """build_delta_payload 含 content。"""
    payload = build_delta_payload("hello")
    assert payload == {"content": "hello"}


def test_build_done_payload() -> None:
    """build_done_payload 含 trace_id 与 finish_reason。"""
    payload = build_done_payload("trace-1", "stop")
    assert payload == {"trace_id": "trace-1", "finish_reason": "stop"}


def test_build_done_payload_default_finish_reason() -> None:
    """build_done_payload 默认 finish_reason='stop'。"""
    payload = build_done_payload("trace-1")
    assert payload["finish_reason"] == "stop"


def test_build_error_payload() -> None:
    """build_error_payload 含 trace_id / code / message。"""
    payload = build_error_payload(code=30001, message="失败", trace_id="t-1")
    assert payload == {"trace_id": "t-1", "code": 30001, "message": "失败"}


# ---------- serialize_event ----------


def test_serialize_event_format() -> None:
    """serialize_event 返回 {event, data(json str)}。"""
    event = serialize_event(EVENT_START, {"trace_id": "t-1"})
    assert event["event"] == "start"
    assert isinstance(event["data"], str)
    parsed = json.loads(event["data"])
    assert parsed == {"trace_id": "t-1"}


def test_serialize_event_ensure_ascii_false() -> None:
    """serialize_event 中文不被转义（ensure_ascii=False）。"""
    event = serialize_event(EVENT_DELTA, {"content": "你好"})
    assert "你好" in event["data"]


# ---------- stream_sse_events 正常流程 ----------


@pytest.mark.asyncio
async def test_stream_sse_events_normal_flow() -> None:
    """正常流程：start → delta* → done。"""

    async def chunk_iter() -> AsyncIterator[ChatChunk]:
        yield ChatChunk(delta="你好", finish_reason=None)
        yield ChatChunk(delta="世界", finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")

    events: list[dict[str, Any]] = []
    async for event in stream_sse_events(chunk_iter(), trace_id="trace-normal"):
        events.append(event)

    # 至少 4 个事件：start + 2 delta + done
    assert len(events) >= 4
    # 第一个是 start
    assert events[0]["event"] == EVENT_START
    start_data = json.loads(events[0]["data"])
    assert start_data["trace_id"] == "trace-normal"
    # 中间是 delta
    delta_events = [e for e in events if e["event"] == EVENT_DELTA]
    assert len(delta_events) == 2
    deltas = [json.loads(e["data"])["content"] for e in delta_events]
    assert deltas == ["你好", "世界"]
    # 最后是 done
    assert events[-1]["event"] == EVENT_DONE
    done_data = json.loads(events[-1]["data"])
    assert done_data["trace_id"] == "trace-normal"
    assert done_data["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_stream_sse_events_empty_delta_skipped() -> None:
    """空 delta 的 chunk 不发送 delta 事件。"""

    async def chunk_iter() -> AsyncIterator[ChatChunk]:
        yield ChatChunk(delta="", finish_reason=None)  # 空 delta
        yield ChatChunk(delta="有内容", finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")

    events: list[dict[str, Any]] = []
    async for event in stream_sse_events(chunk_iter(), trace_id="t"):
        events.append(event)

    delta_events = [e for e in events if e["event"] == EVENT_DELTA]
    # 只有 1 个 delta（"有内容"）
    assert len(delta_events) == 1
    assert json.loads(delta_events[0]["data"])["content"] == "有内容"


# ---------- stream_sse_events 异常流程 ----------


@pytest.mark.asyncio
async def test_stream_sse_events_ragent_exception_sends_error() -> None:
    """RagentException → 发送 error 事件（含 code）。"""

    async def chunk_iter() -> AsyncIterator[ChatChunk]:
        yield ChatChunk(delta="部分", finish_reason=None)
        raise BizException(message="业务异常", code=10501)
        yield  # type: ignore[unreachable]

    events: list[dict[str, Any]] = []
    async for event in stream_sse_events(chunk_iter(), trace_id="t-err"):
        events.append(event)

    error_events = [e for e in events if e["event"] == EVENT_ERROR]
    assert len(error_events) == 1
    err_data = json.loads(error_events[0]["data"])
    assert err_data["code"] == 10501
    assert err_data["message"] == "业务异常"
    assert err_data["trace_id"] == "t-err"
    # 异常后不应有 done 事件
    done_events = [e for e in events if e["event"] == EVENT_DONE]
    assert len(done_events) == 0


@pytest.mark.asyncio
async def test_stream_sse_events_generic_exception_sends_error() -> None:
    """未知异常 → 发送通用 error 事件（默认 code）。"""

    async def chunk_iter() -> AsyncIterator[ChatChunk]:
        # yield 使其成为 async generator（空 delta 不会发送 delta 事件）
        yield ChatChunk(delta="", finish_reason=None)
        raise RuntimeError("未知错误")

    events: list[dict[str, Any]] = []
    async for event in stream_sse_events(chunk_iter(), trace_id="t-generic"):
        events.append(event)

    error_events = [e for e in events if e["event"] == EVENT_ERROR]
    assert len(error_events) == 1
    err_data = json.loads(error_events[0]["data"])
    assert err_data["code"] == 30001
    assert err_data["trace_id"] == "t-generic"


@pytest.mark.asyncio
async def test_stream_sse_events_cancelled_does_not_raise() -> None:
    """客户端断开（CancelledError）不抛异常，不发送 error。"""

    async def chunk_iter() -> AsyncIterator[ChatChunk]:
        yield ChatChunk(delta="start", finish_reason=None)
        raise asyncio.CancelledError()

    events: list[dict[str, Any]] = []
    # 不应抛异常
    async for event in stream_sse_events(chunk_iter(), trace_id="t-cancel"):
        events.append(event)

    # 至少有 start 事件
    assert events[0]["event"] == EVENT_START
    # 不应有 error 或 done（客户端已断开）
    assert not any(e["event"] == EVENT_ERROR for e in events)
    assert not any(e["event"] == EVENT_DONE for e in events)


@pytest.mark.asyncio
async def test_stream_sse_events_start_always_first() -> None:
    """start 事件总是第一个发送（即使迭代器为空）。"""

    async def empty_iter() -> AsyncIterator[ChatChunk]:
        return
        yield  # type: ignore[unreachable]

    events: list[dict[str, Any]] = []
    async for event in stream_sse_events(empty_iter(), trace_id="t-empty"):
        events.append(event)

    # 空迭代器：start + done
    assert len(events) == 2
    assert events[0]["event"] == EVENT_START
    assert events[1]["event"] == EVENT_DONE
