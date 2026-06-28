"""统一响应 ApiResponse[T]。

放在 framework/core（framework 无业务依赖），供 schemas 层 re-export 与
framework/middleware 引用，避免 framework→schemas 的反向依赖。

响应结构：{ code, message, data, trace_id }
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from ragent.framework.core.config import get_settings
from ragent.framework.trace.context import get_trace_id

T = TypeVar("T")

# 成功响应统一码
SUCCESS_CODE = 0
SUCCESS_MESSAGE = "OK"


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应体。

    Attributes:
        code: 0 表示成功，非 0 表示错误（按错误码段位区分异常类型）
        message: 响应消息（错误时为用户可见错误信息，禁止包含堆栈）
        data: 响应数据（成功时为业务数据，错误时为 None）
        trace_id: 链路追踪 ID（从 contextvars 获取，便于问题定位）
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int
    message: str
    data: T | None = None
    trace_id: str = ""

    @classmethod
    def success(cls, data: T | None = None, message: str = SUCCESS_MESSAGE) -> ApiResponse[T]:
        """构造成功响应。"""
        return cls(
            code=SUCCESS_CODE,
            message=message,
            data=data,
            trace_id=get_trace_id(),
        )

    @classmethod
    def error(cls, code: int, message: str) -> ApiResponse[T]:
        """构造错误响应（trace_id 自动注入）。"""
        return cls(
            code=code,
            message=message,
            data=None,
            trace_id=get_trace_id(),
        )


class PageResponse(BaseModel, Generic[T]):
    """分页响应体。

    Attributes:
        items: 当前页数据
        total: 总条数
        page: 当前页码（从 1 开始）
        page_size: 每页大小
        trace_id: 链路追踪 ID
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    trace_id: str = ""

    @classmethod
    def of(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResponse[T]:
        """构造分页响应。"""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            trace_id=get_trace_id(),
        )


def get_app_name() -> str:
    """获取应用名（供 health 接口引用，避免 health 直接耦合 Settings 结构）。"""
    try:
        return get_settings().app.name
    except Exception:
        return "ragent-py"


__all__ = [
    "ApiResponse",
    "PageResponse",
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
    "get_app_name",
]
