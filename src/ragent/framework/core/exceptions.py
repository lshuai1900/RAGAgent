"""三级异常体系。

- RagentException：所有项目异常基类
- BizException（业务异常，错误码段位 1xxxx，HTTP 400）
- SysException（系统异常，错误码段位 2xxxx，HTTP 500）
- InfraException（基础设施异常，错误码段位 3xxxx，HTTP 503）

异常为纯领域无关的通用基础设施，framework 不依赖任何业务层。
"""

from __future__ import annotations


class RagentException(Exception):
    """Ragent-Py 所有异常的基类。

    Attributes:
        code: 错误码（int，按段位区分类型）
        message: 错误信息（用户可见，禁止包含敏感信息与堆栈）
        http_status: 对应 HTTP 状态码
    """

    code: int = 20000
    message: str = "Internal Server Error"
    http_status: int = 500

    def __init__(
        self,
        message: str | None = None,
        code: int | None = None,
        http_status: int | None = None,
        *,
        cause: BaseException | None = None,
    ) -> None:
        self.code = code if code is not None else self.__class__.code
        self.message = message if message is not None else self.__class__.message
        self.http_status = http_status if http_status is not None else self.__class__.http_status
        self.__cause__ = cause
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code}, message={self.message!r})"


class BizException(RagentException):
    """业务异常：用户请求语义错误、参数校验失败、业务规则不满足。

    错误码段位：10000-19999，HTTP 400。
    """

    code = 10000
    message = "Business Error"
    http_status = 400


class SysException(RagentException):
    """系统异常：服务内部错误、状态不一致、未预期分支。

    错误码段位：20000-29999，HTTP 500。
    """

    code = 20000
    message = "System Error"
    http_status = 500


class InfraException(RagentException):
    """基础设施异常：DB / Milvus / LLM 等外部依赖不可用。

    错误码段位：30000-39999，HTTP 503。
    """

    code = 30000
    message = "Infrastructure Error"
    http_status = 503


__all__ = [
    "BizException",
    "InfraException",
    "RagentException",
    "SysException",
]
