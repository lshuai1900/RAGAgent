"""FastAPI 依赖注入：提供 service 实例。

职责：
- 通过 Depends(get_session) 获取请求级 AsyncSession
- 构造 repository / embedding_client / vector_store / pipeline / service 实例
- 实例范围为单请求（不缓存）

约束：
- api 层只通过本文件依赖获取 service，不直接 new repository / infra_ai / rag 实例
- embedding_client / vector_store 为模块级单例（应用级共享），由 factory 构建一次
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.framework.db.session import get_session
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.factory import build_embedding_client
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.persistence.repositories.chunk_repo import DocumentChunkRepository
from ragent.persistence.repositories.document_repo import DocumentRepository
from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository
from ragent.rag.vector.base import BaseVectorStore
from ragent.rag.vector.milvus import MilvusVectorStore
from ragent.service.ingestion_service import IngestionService
from ragent.service.knowledge_service import KnowledgeService


@lru_cache(maxsize=1)
def get_embedding_client() -> BaseEmbeddingClient:
    """应用级单例 Embedding 客户端（按 Settings 构建）。"""
    return build_embedding_client()


@lru_cache(maxsize=1)
def get_vector_store() -> BaseVectorStore:
    """应用级单例 MilvusVectorStore。"""
    return MilvusVectorStore()


@lru_cache(maxsize=1)
def get_pipeline() -> IngestionPipeline:
    """应用级单例 IngestionPipeline（共享 embedding_client + vector_store）。"""
    return IngestionPipeline(
        embedding_client=get_embedding_client(),
        vector_store=get_vector_store(),
    )


def get_kb_repo(
    session: AsyncSession = Depends(get_session),
) -> KnowledgeBaseRepository:
    """请求级 KnowledgeBaseRepository。"""
    return KnowledgeBaseRepository(session)


def get_document_repo(
    session: AsyncSession = Depends(get_session),
) -> DocumentRepository:
    """请求级 DocumentRepository。"""
    return DocumentRepository(session)


def get_chunk_repo(
    session: AsyncSession = Depends(get_session),
) -> DocumentChunkRepository:
    """请求级 DocumentChunkRepository。"""
    return DocumentChunkRepository(session)


def get_knowledge_service(
    kb_repo: KnowledgeBaseRepository = Depends(get_kb_repo),
    vector_store: BaseVectorStore = Depends(get_vector_store),
    embedding_client: BaseEmbeddingClient = Depends(get_embedding_client),
) -> KnowledgeService:
    """请求级 KnowledgeService。"""
    return KnowledgeService(
        kb_repo=kb_repo,
        vector_store=vector_store,
        embedding_client=embedding_client,
    )


def get_ingestion_service(
    kb_repo: KnowledgeBaseRepository = Depends(get_kb_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
    pipeline: IngestionPipeline = Depends(get_pipeline),
) -> IngestionService:
    """请求级 IngestionService。"""
    return IngestionService(
        kb_repo=kb_repo,
        document_repo=document_repo,
        pipeline=pipeline,
    )


__all__ = [
    "get_chunk_repo",
    "get_document_repo",
    "get_embedding_client",
    "get_ingestion_service",
    "get_kb_repo",
    "get_knowledge_service",
    "get_pipeline",
    "get_vector_store",
]


# 重新导出 get_session，便于 api 层统一从 deps 导入
# （不创建新的依赖函数，避免覆盖请求级 session 行为）
async def get_request_session() -> AsyncIterator[AsyncSession]:
    """请求级 session 依赖（与 framework.db.session.get_session 行为一致）。

    api 层若需直接使用 session（如手动构造 repo），通过本依赖获取。
    """
    async for session in get_session():
        yield session
