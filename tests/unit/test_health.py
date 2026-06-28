"""health 接口测试。

使用 httpx.AsyncClient + ASGITransport 直接调用 FastAPI app，
不依赖真实 PostgreSQL / Milvus（依赖项不可达时返回 degraded/error，不报错）。

验证：
- /health 返回 200
- 响应包含 trace_id（X-Trace-Id 头）
- 响应结构符合 ApiResponse[HealthResponse]
- 组件状态包含 postgres 与 milvus
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from httpx import ASGITransport

from ragent.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """构造 ASGI 测试客户端。"""
    app = create_app()
    transport = ASGITransport(app=app)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        yield c


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncIterator[httpx.AsyncClient]) -> None:
    """/health 返回 200。"""
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_response_structure(client: AsyncIterator[httpx.AsyncClient]) -> None:
    """/health 响应结构符合 ApiResponse[HealthResponse]。"""
    resp = await client.get("/health")
    body = resp.json()
    # ApiResponse 字段
    assert "code" in body
    assert "message" in body
    assert "data" in body
    assert "trace_id" in body
    assert body["code"] == 0
    # HealthResponse 字段
    data = body["data"]
    assert "status" in data
    assert "app" in data
    assert "env" in data
    assert "timestamp" in data
    assert "components" in data
    # components 包含 postgres 与 milvus
    assert "postgres" in data["components"]
    assert "milvus" in data["components"]


@pytest.mark.asyncio
async def test_health_trace_id_in_response_header(
    client: AsyncIterator[httpx.AsyncClient],
) -> None:
    """响应头包含 X-Trace-Id。"""
    resp = await client.get("/health")
    assert "x-trace-id" in resp.headers
    trace_id = resp.headers["x-trace-id"]
    assert trace_id  # 非空
    # trace_id 应与 body 中一致
    body = resp.json()
    assert body["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_health_inherits_trace_id_from_request(
    client: AsyncIterator[httpx.AsyncClient],
) -> None:
    """请求头携带 X-Trace-Id 时，响应继承该值。"""
    custom_trace = "my-custom-trace-id-12345"
    resp = await client.get("/health", headers={"X-Trace-Id": custom_trace})
    assert resp.headers["x-trace-id"] == custom_trace
    body = resp.json()
    assert body["trace_id"] == custom_trace


@pytest.mark.asyncio
async def test_health_status_values(client: AsyncIterator[httpx.AsyncClient]) -> None:
    """整体状态值为 ok / degraded / error 之一。"""
    resp = await client.get("/health")
    data = resp.json()["data"]
    assert data["status"] in {"ok", "degraded", "error"}
    # 组件状态值为 ok / error
    for comp in data["components"].values():
        assert comp["status"] in {"ok", "error"}
