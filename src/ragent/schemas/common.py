"""API 公共 Schema。

schemas 层顶层独立，可依赖 framework（通用基础设施），但不得被 domain 依赖。
ApiResponse / PageResponse 定义在 framework/core/response.py（避免 framework→schemas 反向依赖），
此处 re-export 供 service / api 层引用，保持 import 路径统一为 schemas.common。
"""

from __future__ import annotations

from ragent.framework.core.response import (
    SUCCESS_CODE,
    SUCCESS_MESSAGE,
    ApiResponse,
    PageResponse,
)

__all__ = [
    "ApiResponse",
    "PageResponse",
    "SUCCESS_CODE",
    "SUCCESS_MESSAGE",
]
