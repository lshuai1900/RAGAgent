"""数据库 async engine + session factory。

使用 SQLAlchemy 2.0 async + asyncpg。
engine 为模块级单例（应用生命周期内复用），session 按请求创建。
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ragent.framework.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """获取全局 async engine（懒初始化单例）。"""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.db.url,
            pool_size=settings.db.pool_size,
            max_overflow=settings.db.max_overflow,
            echo=settings.db.echo,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取 async session factory（懒初始化单例）。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：提供请求级 async session，请求结束自动关闭。"""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def dispose_engine() -> None:
    """释放 engine 资源（应用关闭时调用）。"""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
