"""trace_id 上下文：基于 contextvars 透传，跨 async 链路不丢失。

MVP 仅实现 trace_id 透传，不实现复杂 Span 树。
"""

from __future__ import annotations

import contextvars
from collections.abc import Mapping
from typing import Any

# trace_id 通过 contextvars 贯穿 async 链路，禁止用全局变量。
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def get_trace_id() -> str:
    """获取当前上下文的 trace_id。"""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> contextvars.Token[str]:
    """设置 trace_id，返回 token 用于复位。"""
    return trace_id_var.set(trace_id)


def reset_trace_id(token: contextvars.Token[str]) -> None:
    """复位 trace_id 到设置前的状态。"""
    trace_id_var.reset(token)


def bind_context(**kwargs: Any) -> Mapping[str, Any]:
    """绑定额外上下文字段到 structlog contextvars（预留，MVP 仅 trace_id）。"""
    # 延迟导入 structlog，避免 framework 顶层硬依赖第三方
    import structlog

    return structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """清空 structlog 上下文绑定。"""
    import structlog

    structlog.contextvars.clear_contextvars()
