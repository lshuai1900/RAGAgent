"""去重后处理器：按 chunk_id 去重，保留最高分。

MVP 仅实现按 chunk_id 去重（同一 chunk 可能被多次命中）。
不实现 Rerank、不实现内容相似度去重。
"""

from __future__ import annotations

from ragent.domain.dto import RetrievalResult
from ragent.framework.core.logging import get_logger
from ragent.rag.retrieve.postprocessor.base import BasePostProcessor

_logger = get_logger(__name__)

# 去重处理器在链中的执行顺序（小先执行）
_DEDUP_ORDER = 1


class DeduplicationPostProcessor(BasePostProcessor):
    """按 chunk_id 去重的后处理器。

    同一 chunk_id 出现多次时，保留 score 最高的那条。
    保持原有的相对顺序（首次出现位置）。
    """

    async def process(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """按 chunk_id 去重，保留最高分。

        Args:
            query: 原始查询文本（本处理器不使用）
            results: 待去重的检索结果列表

        Returns:
            去重后的列表，按首次出现顺序排列；同 chunk_id 保留最高分
        """
        if not results:
            return []

        best_by_chunk: dict[str, RetrievalResult] = {}
        order: list[str] = []
        for r in results:
            cid = r.chunk_id
            if cid not in best_by_chunk:
                best_by_chunk[cid] = r
                order.append(cid)
            else:
                existing = best_by_chunk[cid]
                if r.score > existing.score:
                    best_by_chunk[cid] = r

        deduped = [best_by_chunk[cid] for cid in order]
        if len(deduped) != len(results):
            _logger.info(
                "dedup_postprocessor_done",
                before=len(results),
                after=len(deduped),
                removed=len(results) - len(deduped),
            )
        return deduped

    def order(self) -> int:
        """返回执行顺序。"""
        return _DEDUP_ORDER


__all__ = ["DeduplicationPostProcessor"]
