"""SSE 事件流封装：start / delta / done / error 四类事件。

技术选型：sse-starlette 的 EventSourceResponse。
事件格式：event: {type}\ndata: {json}\n\n

四类事件 JSON 结构：
- start:  {"trace_id": "..."}
- delta:  {"content": "..."}
- done:   {"trace_id": "...", "finish_reason": "stop"}
- error:  {"trace_id": "...", "code": 30001, "message": "..."}

约束：
- 错误事件携带 trace_id 便于排查
- 客户端断开（asyncio.CancelledError / ConnectionError）不导致进程崩溃
- 不泄露堆栈给客户端
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from ragent.framework.core.exceptions import RagentException
from ragent.framework.core.logging import get_logger
from ragent.framework.trace.context import get_trace_id

_logger = get_logger(__name__)

# SSE 事件类型常量
EVENT_START = "start"
EVENT_DELTA = "delta"
EVENT_DONE = "done"
EVENT_ERROR = "error"

# 默认错误码（基础设施异常段位）
_DEFAULT_ERROR_CODE = 30001
_DEFAULT_ERROR_MESSAGE = "SSE 流式问答失败"


def build_start_payload(trace_id: str | None = None) -> dict[str, Any]:
    """构造 start 事件 payload。"""
    return {"trace_id": trace_id or get_trace_id()}


def build_delta_payload(content: str) -> dict[str, Any]:
    """构造 delta 事件 payload。"""
    return {"content": content}


def build_done_payload(
    trace_id: str | None = None,
    finish_reason: str = "stop",
) -> dict[str, Any]:
    """构造 done 事件 payload。"""
    return {
        "trace_id": trace_id or get_trace_id(),
        "finish_reason": finish_reason,
    }


def build_error_payload(
    code: int = _DEFAULT_ERROR_CODE,
    message: str = _DEFAULT_ERROR_MESSAGE,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """构造 error 事件 payload。"""
    return {
        "trace_id": trace_id or get_trace_id(),
        "code": code,
        "message": message,
    }


def serialize_event(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """构造 sse-starlette EventSourceResponse 所需的事件 dict。

    sse-starlette 接收 {"event": ..., "data": ...}，data 必须是字符串。

    Args:
        event: 事件类型（start/delta/done/error）
        payload: 事件数据 dict

    Returns:
        {"event": event, "data": json_str}
    """
    return {
        "event": event,
        "data": json.dumps(payload, ensure_ascii=False),
    }


async def stream_sse_events(
    chunk_iterator: AsyncIterator[Any],
    *,
    trace_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """把 ChatChunk 异步迭代器转换为 SSE 事件流。

    流程：
    1. 立即发送 start 事件（含 trace_id）
    2. 遍历 chunk_iterator，每个 ChatChunk 的 delta 转为 delta 事件
    3. 正常结束后发送 done 事件
    4. 异常时发送 error 事件（含 trace_id），不泄露堆栈

    客户端断开（asyncio.CancelledError / ConnectionError）仅记录日志，不抛异常。

    Args:
        chunk_iterator: ChatChunk 异步迭代器（来自 ChatService.stream_chat）
        trace_id: 可选 trace_id，None 时从 contextvars 获取

    Yields:
        sse-starlette 事件 dict
    """
    tid = trace_id or get_trace_id()

    # 1. start 事件
    yield serialize_event(EVENT_START, build_start_payload(tid))

    finish_reason = "stop"
    try:
        async for chunk in chunk_iterator:
            # chunk 为 ChatChunk，含 delta 与 finish_reason
            delta = getattr(chunk, "delta", "")
            fr = getattr(chunk, "finish_reason", None)
            if fr is not None:
                finish_reason = fr
            if delta:
                yield serialize_event(EVENT_DELTA, build_delta_payload(delta))

        # 3. done 事件
        yield serialize_event(EVENT_DONE, build_done_payload(tid, finish_reason))

    except asyncio.CancelledError:
        # 客户端断开连接：仅记录日志，不抛异常，不发送 error（连接已断）
        _logger.info("sse_client_disconnected", trace_id=tid)
        # 不 re-raise，避免进程崩溃
        return

    except ConnectionError as exc:
        # 网络异常：仅记录日志，不抛异常
        _logger.warning("sse_connection_error", trace_id=tid, error=str(exc))
        return

    except RagentException as exc:
        # 项目自定义异常：发送 error 事件，携带 code 与 message
        _logger.warning(
            "sse_ragent_exception",
            trace_id=tid,
            code=exc.code,
            message=exc.message,
        )
        try:
            yield serialize_event(
                EVENT_ERROR,
                build_error_payload(
                    code=exc.code,
                    message=exc.message,
                    trace_id=tid,
                ),
            )
        except Exception:  # noqa: BLE001
            # 发送 error 事件本身失败（客户端已断），仅记录日志
            _logger.warning("sse_error_event_send_failed", trace_id=tid)

    except Exception as exc:  # noqa: BLE001
        # 未捕获异常：发送通用 error 事件，不泄露堆栈
        _logger.error(
            "sse_uncaught_exception",
            trace_id=tid,
            error=str(exc),
            exc_info=True,
        )
        try:
            yield serialize_event(
                EVENT_ERROR,
                build_error_payload(
                    code=_DEFAULT_ERROR_CODE,
                    message=_DEFAULT_ERROR_MESSAGE,
                    trace_id=tid,
                ),
            )
        except Exception:  # noqa: BLE001
            _logger.warning("sse_error_event_send_failed", trace_id=tid)


__all__ = [
    "EVENT_DELTA",
    "EVENT_DONE",
    "EVENT_ERROR",
    "EVENT_START",
    "build_delta_payload",
    "build_done_payload",
    "build_error_payload",
    "build_start_payload",
    "serialize_event",
    "stream_sse_events",
]
