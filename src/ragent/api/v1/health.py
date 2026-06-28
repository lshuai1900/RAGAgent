"""健康检查接口。

GET /health 返回应用状态、PostgreSQL 连通性、Milvus 连通性。

不做任何业务逻辑，仅探测基础设施可用性。
- PostgreSQL：执行 SELECT 1
- Milvus：TCP 端口连通性检查（避免引入 pymilvus 完整客户端）
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import text

from ragent.framework.core.config import get_settings
from ragent.framework.core.response import ApiResponse, get_app_name
from ragent.framework.db.session import get_engine
from ragent.framework.trace.context import get_trace_id

router = APIRouter(tags=["health"])


class ComponentStatus(BaseModel):
    """单个组件健康状态。"""

    status: str  # "ok" / "error"
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str  # "ok" / "degraded" / "error"
    app: str
    env: str
    timestamp: str
    trace_id: str
    components: dict[str, ComponentStatus]


async def _check_postgres() -> ComponentStatus:
    """探测 PostgreSQL 连通性：SELECT 1。"""
    loop = asyncio.get_event_loop()
    started = loop.time()
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = round((loop.time() - started) * 1000, 2)
        return ComponentStatus(status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((loop.time() - started) * 1000, 2)
        return ComponentStatus(
            status="error",
            latency_ms=latency_ms,
            error=f"{exc.__class__.__name__}: {exc}",
        )


async def _check_milvus() -> ComponentStatus:
    """探测 Milvus 连通性。

    支持两种部署形态：
    - 远程 standalone：URI 形如 http://host:19530，走 TCP 端口探测
    - milvus-lite 本地文件：URI 形如 ./milvus.db，尝试创建客户端验证
    """
    from urllib.parse import urlparse

    loop = asyncio.get_event_loop()
    settings = get_settings()
    uri = settings.milvus.uri
    parsed = urlparse(uri)

    started = loop.time()
    try:
        if not parsed.scheme:
            # milvus-lite 本地文件：创建客户端验证连通性
            from pymilvus import AsyncMilvusClient

            client = AsyncMilvusClient(uri=uri)
            await asyncio.wait_for(client.list_collections(), timeout=2.0)
            await client.close()
        else:
            # 远程 standalone：TCP 端口探测
            host = parsed.hostname or "localhost"
            port = parsed.port or 19530
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2.0)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
        latency_ms = round((loop.time() - started) * 1000, 2)
        return ComponentStatus(status="ok", latency_ms=latency_ms)
    except Exception as exc:  # noqa: BLE001
        latency_ms = round((loop.time() - started) * 1000, 2)
        return ComponentStatus(
            status="error",
            latency_ms=latency_ms,
            error=f"{exc.__class__.__name__}: {exc}",
        )


def _aggregate_status(components: dict[str, ComponentStatus]) -> str:
    """汇总各组件状态得到整体状态。"""
    if not components:
        return "ok"
    if all(c.status == "ok" for c in components.values()):
        return "ok"
    if any(c.status == "ok" for c in components.values()):
        return "degraded"
    return "error"


@router.get(
    "/health",
    response_model=ApiResponse[HealthResponse],
    status_code=status.HTTP_200_OK,
)
async def health() -> ApiResponse[HealthResponse]:
    """健康检查：返回应用状态、PG/Milvus 连通性。

    不做业务逻辑，仅探测基础设施。
    """
    settings = get_settings()
    pg_status, milvus_status = await asyncio.gather(_check_postgres(), _check_milvus())
    components: dict[str, ComponentStatus] = {
        "postgres": pg_status,
        "milvus": milvus_status,
    }
    overall = _aggregate_status(components)
    payload = HealthResponse(
        status=overall,
        app=get_app_name(),
        env=settings.app.env,
        timestamp=datetime.now(UTC).isoformat(),
        trace_id=get_trace_id(),
        components=components,
    )
    return ApiResponse.success(data=payload)


__all__ = ["ComponentStatus", "HealthResponse", "router"]
