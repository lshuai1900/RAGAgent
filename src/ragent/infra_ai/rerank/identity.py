"""Identity Reranker：直通不排序（MVP 默认）。

不调用真实 Rerank 模型，仅按原始顺序截断 top_k。
MVP 锁定使用本实现，暂缓 Rerank 模型调用。
"""

from __future__ import annotations

from ragent.domain.dto import RetrievalResult
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.rerank.base import BaseReranker

_logger = get_logger(__name__)


class IdentityReranker(BaseReranker):
    """直通 Reranker。

    - rerank: 不排序，直接截断 top_k（保持原始顺序）
    - enabled: True（启用但直通，便于在编排链中统一调用）
    """

    async def rerank(
        self,
        query: str,
        candidates: list[RetrievalResult],
        top_k: int,
    ) -> list[RetrievalResult]:
        """直通返回前 top_k 条（不排序）。

        Args:
            query: 查询文本（本实现不使用）
            candidates: 候选检索结果
            top_k: 返回前 K 条

        Returns:
            前 top_k 条候选（保持原始顺序）
        """
        if top_k <= 0:
            return []
        result = candidates[:top_k]
        _logger.info(
            "identity_rerank_done",
            candidates=len(candidates),
            returned=len(result),
            top_k=top_k,
        )
        return result

    def enabled(self) -> bool:
        """启用但直通。"""
        return True


__all__ = ["IdentityReranker"]
