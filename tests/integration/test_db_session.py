"""数据库 session 连通性测试。

集成测试：依赖 docker-compose 启动的 PostgreSQL。
未启动 PG 时，测试将被 skip（避免 CI 失败）。

验证：
- get_engine 返回单例
- get_session_factory 返回单例
- get_session 依赖可正常 yield session
- SELECT 1 可执行
"""

from __future__ import annotations

import contextlib
import socket
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from ragent.framework.core.config import get_settings, reload_settings
from ragent.framework.db.session import (
    dispose_engine,
    get_engine,
    get_session,
    get_session_factory,
)


def _pg_reachable() -> bool:
    """探测 PG 是否可达（避免无 PG 时测试失败）。"""
    settings = get_settings()
    # 解析 postgresql+asyncpg://user:pwd@host:port/db
    uri = settings.db.url
    try:
        if "://" in uri:
            _, rest = uri.split("://", 1)
        else:
            rest = uri
        if "@" in rest:
            _, host_port_db = rest.split("@", 1)
        else:
            host_port_db = rest
        host_port = host_port_db.split("/", 1)[0]
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host, port = host_port, 5432
    except Exception:  # noqa: BLE001
        return False

    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


@pytest.fixture
async def _ensure_pg() -> AsyncIterator[None]:
    """PG 不可达时 skip 测试，可达时执行并在结束后释放 engine。"""
    reload_settings()
    if not _pg_reachable():
        pytest.skip("PostgreSQL 不可达，跳过集成测试")
    yield
    await dispose_engine()


@pytest.mark.asyncio
async def test_get_engine_returns_singleton(_ensure_pg: AsyncIterator[None]) -> None:
    """get_engine 返回同一实例（单例）。"""
    engine1 = get_engine()
    engine2 = get_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_get_session_factory_returns_singleton(
    _ensure_pg: AsyncIterator[None],
) -> None:
    """get_session_factory 返回同一实例。"""
    f1 = get_session_factory()
    f2 = get_session_factory()
    assert f1 is f2


@pytest.mark.asyncio
async def test_get_session_yields_async_session(
    _ensure_pg: AsyncIterator[None],
) -> None:
    """get_session 依赖可正常 yield AsyncSession。"""
    gen = get_session()
    session = await gen.__anext__()
    try:
        # 简单查询验证连通性
        result = await session.execute(text("SELECT 1"))
        scalar = result.scalar()
        assert scalar == 1
    finally:
        # 关闭 session
        with contextlib.suppress(StopAsyncIteration):
            await gen.aclose()


@pytest.mark.asyncio
async def test_select_one(_ensure_pg: AsyncIterator[None]) -> None:
    """直接通过 engine 执行 SELECT 1。"""
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
