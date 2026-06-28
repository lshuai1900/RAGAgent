"""检索器抽象接口。

BaseRetriever 只依赖 domain.dto.RetrievalResult 与 domain.value_objects.RetrievalQuery，
禁止依赖 persistence / api / rag.vector 等具体实现。
实现类（VectorRetriever）才允许依赖 infra_ai + rag.vector。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import RetrievalResult
from ragent.domain.value_objects import RetrievalQuery


@runtime_checkable
class BaseRetriever(Protocol):
    """检索器抽象接口。

    实现类需提供：
    - retrieve: 按查询文本执行检索，返回 RetrievalResult 列表
    - channel_name: 检索通道标识（MVP: "vector_default"）

    MVP 仅实现 VectorRetriever，不实现意图识别/多路检索/查询改写。
    """

    async def retrieve(
        self,
        query: RetrievalQuery,
        top_k: int,
    ) -> list[RetrievalResult]:
        """执行检索。

        Args:
            query: 检索查询（含文本、kb_id、session_id）
            top_k: 返回前 K 条

        Returns:
            检索结果列表，按相似度从高到低排序
        """
        ...

    def channel_name(self) -> str:
        """检索通道标识（用于 RetrievalResult.retrieval_channel）。"""
        ...


__all__ = ["BaseRetriever"]
