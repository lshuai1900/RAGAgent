"""FastAPI 依赖注入：提供 service 实例。

职责：
- 通过 Depends(get_session) 获取请求级 AsyncSession
- 构造 repository / embedding_client / vector_store / pipeline / service 实例
- 实例范围为单请求（不缓存）

约束：
- api 层只通过本文件依赖获取 service，不直接 new repository / infra_ai / rag 实例
- embedding_client / vector_store / llm_client / reranker 为模块级单例（应用级共享）
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.framework.db.session import get_session
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.factory import (
    build_embedding_client,
    build_llm_client,
    build_reranker,
)
from ragent.infra_ai.llm.base import BaseLLMClient
from ragent.infra_ai.rerank.base import BaseReranker
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.persistence.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from ragent.persistence.repositories.chunk_repo import DocumentChunkRepository
from ragent.persistence.repositories.document_repo import DocumentRepository
from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository
from ragent.rag.memory.base import BaseMemoryStore
from ragent.rag.memory.db_store import DbMemoryStore
from ragent.rag.prompt.service import PromptService
from ragent.rag.retrieve.base import BaseRetriever
from ragent.rag.retrieve.postprocessor.base import BasePostProcessor
from ragent.rag.retrieve.postprocessor.dedup import DeduplicationPostProcessor
from ragent.rag.retrieve.vector_retriever import VectorRetriever
from ragent.rag.vector.base import BaseVectorStore
from ragent.rag.vector.milvus import MilvusVectorStore
from ragent.service.chat_service import ChatService
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
def get_llm_client() -> BaseLLMClient:
    """应用级单例 LLM 客户端（按 Settings 构建）。"""
    return build_llm_client()


@lru_cache(maxsize=1)
def get_reranker() -> BaseReranker:
    """应用级单例 Reranker（MVP: IdentityReranker）。"""
    return build_reranker()


@lru_cache(maxsize=1)
def get_prompt_service() -> PromptService:
    """应用级单例 PromptService。"""
    return PromptService()


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


def get_chat_message_repo(
    session: AsyncSession = Depends(get_session),
) -> ChatMessageRepository:
    """请求级 ChatMessageRepository。"""
    return ChatMessageRepository(session)


def get_chat_session_repo(
    session: AsyncSession = Depends(get_session),
) -> ChatSessionRepository:
    """请求级 ChatSessionRepository。"""
    return ChatSessionRepository(session)


def get_post_processors() -> list[BasePostProcessor]:
    """请求级后处理器链（MVP 仅 DeduplicationPostProcessor）。"""
    return [DeduplicationPostProcessor()]


def get_retriever(
    embedding_client: BaseEmbeddingClient = Depends(get_embedding_client),
    vector_store: BaseVectorStore = Depends(get_vector_store),
    kb_repo: KnowledgeBaseRepository = Depends(get_kb_repo),
) -> BaseRetriever:
    """请求级 VectorRetriever。"""
    return VectorRetriever(
        embedding_client=embedding_client,
        vector_store=vector_store,
        kb_repo=kb_repo,
    )


def get_memory_store(
    chat_message_repo: ChatMessageRepository = Depends(get_chat_message_repo),
    chat_session_repo: ChatSessionRepository = Depends(get_chat_session_repo),
) -> BaseMemoryStore:
    """请求级 DbMemoryStore。"""
    return DbMemoryStore(
        chat_message_repo=chat_message_repo,
        chat_session_repo=chat_session_repo,
    )


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
    chunk_repo: DocumentChunkRepository = Depends(get_chunk_repo),
) -> IngestionService:
    """请求级 IngestionService。"""
    return IngestionService(
        kb_repo=kb_repo,
        document_repo=document_repo,
        pipeline=pipeline,
        chunk_repo=chunk_repo,
    )


def get_chat_service(
    retriever: BaseRetriever = Depends(get_retriever),
    post_processors: list[BasePostProcessor] = Depends(get_post_processors),
    reranker: BaseReranker = Depends(get_reranker),
    llm_client: BaseLLMClient = Depends(get_llm_client),
    memory_store: BaseMemoryStore = Depends(get_memory_store),
    prompt_service: PromptService = Depends(get_prompt_service),
    chat_message_repo: ChatMessageRepository = Depends(get_chat_message_repo),
    chat_session_repo: ChatSessionRepository = Depends(get_chat_session_repo),
) -> ChatService:
    """请求级 ChatService。"""
    return ChatService(
        retriever=retriever,
        post_processors=post_processors,
        reranker=reranker,
        llm_client=llm_client,
        memory_store=memory_store,
        prompt_service=prompt_service,
        chat_message_repo=chat_message_repo,
        chat_session_repo=chat_session_repo,
    )


__all__ = [
    "get_chat_message_repo",
    "get_chat_service",
    "get_chat_session_repo",
    "get_chunk_repo",
    "get_document_repo",
    "get_embedding_client",
    "get_ingestion_service",
    "get_kb_repo",
    "get_knowledge_service",
    "get_llm_client",
    "get_memory_store",
    "get_pipeline",
    "get_post_processors",
    "get_prompt_service",
    "get_reranker",
    "get_retriever",
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
