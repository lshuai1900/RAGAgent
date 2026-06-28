"""Rerank 客户端抽象接口。

BaseReranker 只依赖 domain.dto.RetrievalResult，
禁止依赖 persistence / api。
MVP 仅实现 IdentityReranker（直通不排序），暂缓真实 Rerank 模型调用。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import RetrievalResult


@runtime_checkable
class BaseReranker(Protocol):
    """Rerank 客户端抽象接口。

    实现类需提供：
    - rerank: 对候选结果重排序
    - enabled: 是否启用 Rerank（IdentityReranker.enabled()=True 但直通）

    MVP 仅 IdentityReranker（直通不排序），暂缓真实 Rerank 模型。
    """

    async def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """对候选结果重排序。

        Args:
            query: 查询文本
            candidates: 候选检索结果
            top_k: 返回前 K 条

        Returns:
            重排序后的检索结果列表
        """
        ...

    def enabled(self) -> bool:
        """是否启用 Rerank。"""
        ...


__all__ = ["BaseReranker"]
