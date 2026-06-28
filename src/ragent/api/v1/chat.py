"""对话 API 路由（SSE 流式问答）。

约束：
- api 层只调用 service，不直接访问 retriever / llm_client / memory / repository
- 使用 schemas 做请求/响应模型
- SSE 事件格式：start / delta / done / error

接口：
- POST /api/v1/chat/sse：流式问答（SSE）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from ragent.api.deps import get_chat_service
from ragent.domain.value_objects import ChatOptions
from ragent.framework.sse.emitter import stream_sse_events
from ragent.framework.trace.context import get_trace_id
from ragent.schemas.chat import ChatSseRequest
from ragent.service.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post(
    "/sse",
    status_code=status.HTTP_200_OK,
    summary="流式问答（SSE）",
    description=("基于知识库的流式问答接口。返回 SSE 事件流：start → delta* → done（或 error）。"),
)
async def chat_sse(
    payload: ChatSseRequest,
    service: ChatService = Depends(get_chat_service),
) -> EventSourceResponse:
    """流式问答：检索 + Prompt + LLM 流式生成。

    事件格式：
    - start:  {"trace_id": "..."}
    - delta:  {"content": "..."}
    - done:   {"trace_id": "...", "finish_reason": "stop"}
    - error:  {"trace_id": "...", "code": 30001, "message": "..."}

    客户端断开连接不会导致服务崩溃（emitter 内部捕获 CancelledError）。
    """
    options = ChatOptions(
        temperature=payload.temperature,
        top_p=payload.top_p,
        max_tokens=payload.max_tokens,
    )
    trace_id = get_trace_id()

    chunk_iter = service.stream_chat(
        session_id=payload.session_id,
        kb_id=payload.kb_id,
        question=payload.question,
        top_k=payload.top_k,
        options=options,
    )

    event_stream = stream_sse_events(chunk_iter, trace_id=trace_id)

    return EventSourceResponse(
        event_stream,
        media_type="text/event-stream",
        ping=15,  # 心跳间隔（秒），防止代理超时断开
    )


__all__ = ["router"]
