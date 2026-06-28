"""结构化日志：structlog + trace_id 注入。

每条日志包含 trace_id（从 contextvars 获取）。
MVP 不实现复杂 Span 树，仅 trace_id 透传 + 结构化日志。
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog

from ragent.framework.trace.context import get_trace_id

EventDict = MutableMapping[str, Any]


def _add_trace_id(_logger: Any, _method_name: str, event_dict: EventDict) -> EventDict:
    """structlog processor：注入当前 trace_id。"""
    event_dict["trace_id"] = get_trace_id()
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    """初始化结构化日志。

    使用 structlog + stdlib logging，输出 JSON 格式，每条日志含 trace_id。
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 配置 stdlib logging 作为底层输出
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_trace_id,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取结构化 logger。"""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
