"""FastAPI 应用入口。

职责：
- lifespan：启动时初始化日志，关闭时释放 engine 资源
- 注册中间件：TraceMiddleware（trace_id 注入 + X-Trace-Id 响应头）
- 注册异常处理器：RagentException + Exception 兜底
- 挂载路由：/health、/api/v1/knowledge-bases、/api/v1/documents、/api/v1/chat
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ragent.api.deps import get_embedding_client, get_vector_store
from ragent.api.v1.chat import router as chat_router
from ragent.api.v1.documents import router as documents_router
from ragent.api.v1.health import router as health_router
from ragent.api.v1.knowledge_bases import router as knowledge_bases_router
from ragent.framework.core.config import get_settings
from ragent.framework.core.logging import setup_logging
from ragent.framework.db.session import dispose_engine
from ragent.framework.middleware.exception import register_exception_handlers
from ragent.framework.middleware.trace import TraceMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时初始化日志，关闭时释放 engine。"""
    # 触发 settings 提前加载，配置错误时启动即失败
    get_settings()
    setup_logging(level="INFO")
    # 预热单例（embedding_client / vector_store），失败不阻塞启动
    try:
        get_embedding_client()
        get_vector_store()
    except Exception:  # noqa: BLE001
        pass
    yield
    # 关闭时释放数据库连接池
    await dispose_engine()


def create_app() -> FastAPI:
    """构造 FastAPI 应用实例。"""
    settings = get_settings()
    app = FastAPI(
        title=settings.app.name,
        description="Ragent-Py: Python 复刻版企业级 Agentic RAG 平台",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 中间件：trace_id 注入（必须先注册，确保所有请求都有 trace_id）
    app.add_middleware(TraceMiddleware)

    # CORS：仅允许前端本地开发地址（P1.1 联调最小改动，不修改业务逻辑）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # 异常处理器：统一返回 ApiResponse
    register_exception_handlers(app)

    # 路由挂载
    app.include_router(health_router)
    app.include_router(knowledge_bases_router)
    app.include_router(documents_router)
    app.include_router(chat_router)

    return app


app = create_app()


__all__ = ["app", "create_app", "lifespan"]
