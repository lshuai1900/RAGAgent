"""trace_id 中间件：每个 HTTP 请求注入 trace_id 并写入响应头。

- 从请求头 X-Trace-Id 继承，无则生成新 UUID
- 存入 contextvars 贯穿 async 链路
- 响应头写入 X-Trace-Id
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ragent.framework.trace.context import reset_trace_id, set_trace_id

_TRACE_HEADER = "X-Trace-Id"


def _generate_trace_id() -> str:
    """生成 trace_id（UUID hex，无连字符）。"""
    return uuid.uuid4().hex


class TraceMiddleware(BaseHTTPMiddleware):
    """注入 trace_id 到 contextvars 并写入响应头。"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_id = request.headers.get(_TRACE_HEADER) or _generate_trace_id()
        token = set_trace_id(trace_id)
        try:
            response = await call_next(request)
        finally:
            reset_trace_id(token)
        response.headers[_TRACE_HEADER] = trace_id
        return response
