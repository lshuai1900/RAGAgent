"""向量库抽象接口。

BaseVectorStore 只依赖 domain.dto.VectorRecord / VectorHit，
禁止依赖 persistence / api。实现类（MilvusVectorStore）才允许依赖 pymilvus。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import VectorHit, VectorRecord


@runtime_checkable
class BaseVectorStore(Protocol):
    """向量库抽象接口。

    实现类需提供：
    - ensure_collection: 幂等创建 collection
    - upsert: 批量写入/更新
    - search: 向量近邻检索
    - delete_by_document: 按文档删除
    - drop_collection: 删除 collection
    """

    async def ensure_collection(self, collection_name: str, dim: int) -> None:
        """确保 collection 存在（幂等创建）。

        Args:
            collection_name: collection 名（如 kb_{snowflake_id}）
            dim: 向量维度（决定 collection schema）
        """
        ...

    async def upsert(self, collection_name: str, vectors: list[VectorRecord]) -> int:
        """批量写入/更新向量。

        Args:
            collection_name: collection 名
            vectors: 待写入的向量记录列表

        Returns:
            写入数量
        """
        ...

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filter_expr: str | None = None,
    ) -> list[VectorHit]:
        """向量近邻检索。

        Args:
            collection_name: collection 名
            query_vector: 查询向量
            top_k: 返回前 K 条
            filter_expr: 过滤表达式（如 'document_id == "xxx"'），可空

        Returns:
            命中结果列表，按相似度从高到低排序
        """
        ...

    async def delete_by_document(self, collection_name: str, document_id: str) -> int:
        """按文档删除所有相关向量。

        Args:
            collection_name: collection 名
            document_id: 文档 ID

        Returns:
            删除数量
        """
        ...

    async def drop_collection(self, collection_name: str) -> None:
        """删除 collection（知识库下架场景）。"""
        ...


__all__ = ["BaseVectorStore"]
