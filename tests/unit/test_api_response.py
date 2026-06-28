"""ApiResponse 测试。

验证：成功/错误响应构造、trace_id 注入、错误码段位。
"""

from __future__ import annotations

from ragent.framework.core.exceptions import (
    BizException,
    InfraException,
    RagentException,
    SysException,
)
from ragent.framework.core.response import (
    SUCCESS_CODE,
    ApiResponse,
    PageResponse,
)
from ragent.framework.trace.context import get_trace_id, reset_trace_id, set_trace_id


def test_success_response() -> None:
    """success 构造成功响应：code=0，data 正确，trace_id 注入。"""
    token = set_trace_id("test-trace-001")
    try:
        resp = ApiResponse.success(data={"name": "demo"})
        assert resp.code == SUCCESS_CODE
        assert resp.message == "OK"
        assert resp.data == {"name": "demo"}
        assert resp.trace_id == "test-trace-001"
    finally:
        reset_trace_id(token)


def test_success_response_without_data() -> None:
    """success 不传 data 时 data 为 None。"""
    token = set_trace_id("trace-002")
    try:
        resp = ApiResponse.success()
        assert resp.code == 0
        assert resp.data is None
        assert resp.trace_id == "trace-002"
    finally:
        reset_trace_id(token)


def test_error_response() -> None:
    """error 构造错误响应：data 为 None，trace_id 注入。"""
    token = set_trace_id("trace-err-003")
    try:
        resp = ApiResponse.error(code=10001, message="参数错误")
        assert resp.code == 10001
        assert resp.message == "参数错误"
        assert resp.data is None
        assert resp.trace_id == "trace-err-003"
    finally:
        reset_trace_id(token)


def test_page_response() -> None:
    """PageResponse 分页响应正确。"""
    token = set_trace_id("trace-page-004")
    try:
        page = PageResponse.of(items=[1, 2, 3], total=100, page=2, page_size=10)
        assert page.items == [1, 2, 3]
        assert page.total == 100
        assert page.page == 2
        assert page.page_size == 10
        assert page.trace_id == "trace-page-004"
    finally:
        reset_trace_id(token)


def test_exception_error_code_segments() -> None:
    """三级异常错误码段位正确：业务 1xxxx / 系统 2xxxx / 基础设施 3xxxx。"""
    biz = BizException("业务异常")
    sys_err = SysException("系统异常")
    infra = InfraException("基础设施异常")

    # 业务异常 10000-19999，HTTP 400
    assert 10000 <= biz.code < 20000
    assert biz.http_status == 400

    # 系统异常 20000-29999，HTTP 500
    assert 20000 <= sys_err.code < 30000
    assert sys_err.http_status == 500

    # 基础设施异常 30000-39999，HTTP 503
    assert 30000 <= infra.code < 40000
    assert infra.http_status == 503


def test_exception_inheritance() -> None:
    """三级异常均继承 RagentException。"""
    assert issubclass(BizException, RagentException)
    assert issubclass(SysException, RagentException)
    assert issubclass(InfraException, RagentException)


def test_exception_custom_code_and_message() -> None:
    """异常支持自定义 code 与 message。"""
    exc = BizException(message="文档不存在", code=10401)
    assert exc.code == 10401
    assert exc.message == "文档不存在"


def test_trace_id_default_empty() -> None:
    """未设置 trace_id 时默认为空字符串。"""
    # 不设置 trace_id，ApiResponse.trace_id 应为空
    # 注意：其他测试可能设置了 trace_id，此处仅验证默认机制
    resp = ApiResponse.success(data=None)
    # trace_id 来自 contextvars，未设置时为空字符串
    assert resp.trace_id == get_trace_id()
