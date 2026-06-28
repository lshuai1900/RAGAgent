"""对话 API Schema（Pydantic v2）。

顶层独立，可依赖 domain（用枚举/DTO），不得被 domain 依赖。
严格与 SQLAlchemy ORM Model 分离。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatSseRequest(BaseModel):
    """SSE 流式问答请求。

    使用 JSON body（便于扩展 ChatOptions）。
    """

    session_id: str = Field(..., min_length=1, max_length=64, description="会话 ID")
    kb_id: str = Field(..., min_length=1, max_length=64, description="知识库 ID")
    question: str = Field(..., min_length=1, description="用户问题")
    top_k: int = Field(5, gt=0, le=50, description="检索 top_k")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="采样温度")
    top_p: float = Field(1.0, gt=0.0, le=1.0, description="nucleus sampling")
    max_tokens: int | None = Field(None, gt=0, description="最大输出 token 数")


class ChatMessageOut(BaseModel):
    """对话消息响应。"""

    id: str
    session_id: str
    role: str
    content: str
    retrieval_context: dict[str, Any] | None = None
    trace_id: str | None = None
    token_count: int = 0
    latency_ms: int | None = None
    created_at: datetime


class ChatMessagePage(BaseModel):
    """对话消息分页响应。"""

    items: list[ChatMessageOut]
    total: int
    page: int
    page_size: int


class ChatSessionOut(BaseModel):
    """对话会话响应。"""

    id: str
    kb_id: str | None = None
    user_id: str | None = None
    message_count: int = 0
    status: str = "active"
    created_at: datetime
    updated_at: datetime


__all__ = [
    "ChatMessageOut",
    "ChatMessagePage",
    "ChatSessionOut",
    "ChatSseRequest",
]
