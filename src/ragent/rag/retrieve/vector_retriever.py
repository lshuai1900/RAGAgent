"""向量检索器：编排 embed query → Milvus search → 映射 RetrievalResult。

VectorRetriever 是 MVP 唯一检索通道（channel_name="vector_default"）。
不实现意图识别、多路检索、查询改写。

依赖：
- infra_ai.embedding.base.BaseEmbeddingClient（用于 query 向量化）
- rag.vector.base.BaseVectorStore（用于 Milvus 检索）
- persistence.repositories.knowledge_base_repo.KnowledgeBaseRepository（用于查 collection_name）

实现类才允许依赖 persistence / infra_ai；base 接口（rag/retrieve/base.py）不依赖这些。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ragent.domain.dto import RetrievalResult, VectorHit
from ragent.domain.value_objects import RetrievalQuery
from ragent.framework.core.exceptions import BizException
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.rag.retrieve.base import BaseRetriever
from ragent.rag.vector.base import BaseVectorStore

if TYPE_CHECKING:
    from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository

_logger = get_logger(__name__)

# MVP 唯一检索通道标识
_CHANNEL_NAME = "vector_default"


class VectorRetriever(BaseRetriever):
    """向量检索器。

    编排流程：
    1. 按 kb_id 查 KnowledgeBase 拿到 collection_name 与 embedding_dim
    2. 用 EmbeddingClient 把 query.text 向量化
    3. 用 VectorStore.search 在 Milvus 中检索 top_k 向量
    4. 把 VectorHit 映射为 RetrievalResult
    """

    def __init__(
        self,
        *,
        embedding_client: BaseEmbeddingClient,
        vector_store: BaseVectorStore,
        kb_repo: KnowledgeBaseRepository,
    ) -> None:
        """初始化 VectorRetriever。

        Args:
            embedding_client: Embedding 客户端（用于 query 向量化）
            vector_store: 向量库（用于 Milvus 检索）
            kb_repo: 知识库 Repository（用于查 collection_name / embedding_dim）
        """
        self._embedding_client = embedding_client
        self._vector_store = vector_store
        self._kb_repo = kb_repo

    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int,
    ) -> list[RetrievalResult]:
        """执行向量检索。

        Args:
            query: 检索查询（kb_id 必填，用于定位 collection）
            top_k: 返回前 K 条

        Returns:
            RetrievalResult 列表，按 score 降序

        Raises:
            BizException: kb_id 缺失或知识库不存在
        """
        if not query.text or not query.text.strip():
            return []
        if top_k <= 0:
            return []
        if query.kb_id is None:
            raise BizException(
                message="VectorRetriever 检索必须指定 kb_id（MVP 单 KB 模式）",
                code=10401,
            )

        # 1. 查 KnowledgeBase 拿 collection_name + embedding_dim
        kb = await self._kb_repo.get_by_id(query.kb_id)
        if kb is None:
            raise BizException(
                message=f"知识库不存在: {query.kb_id}",
                code=10404,
            )
        collection_name = kb.collection_name

        # 2. query 向量化
        query_vector = await self._embedding_client.embed_one(query.text)

        # 3. Milvus 检索（按 kb_id 过滤，防止跨 KB 命中）
        filter_expr = f'kb_id == "{query.kb_id}"'
        hits = await self._vector_store.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k,
            filter_expr=filter_expr,
        )

        # 4. 映射为 RetrievalResult
        results = [self._map_hit_to_result(hit, query.kb_id) for hit in hits]

        _logger.info(
            "vector_retrieve_done",
            kb_id=query.kb_id,
            top_k=top_k,
            hit_count=len(results),
            channel=_CHANNEL_NAME,
        )
        return results

    def channel_name(self) -> str:
        """返回检索通道标识。"""
        return _CHANNEL_NAME

    @staticmethod
    def _map_hit_to_result(hit: VectorHit, kb_id: str) -> RetrievalResult:
        """把 VectorHit 映射为 RetrievalResult。

        Args:
            hit: Milvus 命中结果
            kb_id: 查询的 kb_id（覆盖 metadata 中的 kb_id，确保一致）

        Returns:
            RetrievalResult
        """
        metadata = dict(hit.metadata)
        document_id = str(metadata.get("document_id", ""))
        # metadata 中的 kb_id 可能与查询 kb_id 不一致（理论上不会，filter 已限定）
        # 此处以查询 kb_id 为准，保证一致性
        metadata["kb_id"] = kb_id
        return RetrievalResult(
            chunk_id=hit.id,
            document_id=document_id,
            kb_id=kb_id,
            content=hit.content,
            score=hit.score,
            metadata=metadata,
            retrieval_channel=_CHANNEL_NAME,
            rerank_score=None,
        )


__all__ = ["VectorRetriever"]
