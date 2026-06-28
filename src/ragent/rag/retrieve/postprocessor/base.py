"""检索后处理器抽象接口。

BasePostProcessor 只依赖 domain.dto.RetrievalResult，
禁止依赖 persistence / api。
实现类（DeduplicationPostProcessor 等）才允许依赖 domain。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import RetrievalResult


@runtime_checkable
class BasePostProcessor(Protocol):
    """检索后处理器抽象接口。

    实现类需提供：
    - process: 对检索结果做后处理（去重、过滤、Rerank 等）
    - order: 链中执行顺序（小先执行），MVP 仅 DeduplicationPostProcessor(order=1)

    MVP 仅实现 DeduplicationPostProcessor，不实现 RerankPostProcessor。
    """

    async def process(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """对检索结果做后处理。

        Args:
            query: 原始查询文本（Rerank 场景可能需要）
            results: 待处理的检索结果列表

        Returns:
            处理后的检索结果列表
        """
        ...

    def order(self) -> int:
        """链中执行顺序（小先执行）。"""
        ...


__all__ = ["BasePostProcessor"]
