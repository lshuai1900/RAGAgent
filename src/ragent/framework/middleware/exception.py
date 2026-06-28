"""全局异常拦截器。

通过 FastAPI 的 exception_handler 机制注册：
- RagentException 子类：按异常自身 http_status 与 code 返回 ApiResponse
- Exception（未捕获）：返回 500 + code 20000，不泄露堆栈

错误响应统一返回 ApiResponse JSON。
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ragent.framework.core.exceptions import RagentException
from ragent.framework.core.logging import get_logger
from ragent.framework.trace.context import get_trace_id

# 未捕获异常的兜底错误码
_UNCAUGHT_CODE = 20000
_UNCAUGHT_MESSAGE = "Internal Server Error"
_UNCAUGHT_STATUS = 500

_logger = get_logger(__name__)


def _build_error_response(
    code: int,
    message: str,
    http_status: int,
) -> JSONResponse:
    """构造统一错误 JSONResponse（trace_id 自动注入）。"""
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "data": None,
        "trace_id": get_trace_id(),
    }
    return JSONResponse(status_code=http_status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器到 FastAPI app。

    处理顺序：
    1. RagentException：项目自定义异常，按 code/http_status 返回
    2. Exception：未捕获异常兜底，统一 500 + 20000，记录堆栈到日志但不返回给客户端
    """

    @app.exception_handler(RagentException)
    async def _handle_ragent_exception(_request: Request, exc: RagentException) -> JSONResponse:
        # 业务/系统/基础设施异常：按异常携带的 code 与 http_status 返回
        _logger.warning(
            "ragent_exception_raised",
            code=exc.code,
            message=exc.message,
            http_status=exc.http_status,
            exception_class=exc.__class__.__name__,
        )
        return _build_error_response(exc.code, exc.message, exc.http_status)

    @app.exception_handler(Exception)
    async def _handle_uncaught_exception(_request: Request, exc: Exception) -> JSONResponse:
        # 未捕获异常：不泄露堆栈给客户端，仅记录完整堆栈到日志
        _logger.error(
            "uncaught_exception",
            exception_class=exc.__class__.__name__,
            message=str(exc),
            exc_info=True,
        )
        return _build_error_response(_UNCAUGHT_CODE, _UNCAUGHT_MESSAGE, _UNCAUGHT_STATUS)


__all__ = ["register_exception_handlers"]
