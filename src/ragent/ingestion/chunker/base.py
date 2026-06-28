"""分块器抽象接口。

BaseChunker 只依赖 domain.dto.ChunkDraft / domain.value_objects.ChunkConfig，
禁止依赖 persistence / infra_ai / rag / api。
实现类（FixedSizeChunker / SentenceChunker / RecursiveChunker）放在同包具体文件。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ragent.domain.dto import ChunkDraft, ParsedDocument
from ragent.domain.value_objects import ChunkConfig


@runtime_checkable
class BaseChunker(Protocol):
    """分块器抽象接口。

    实现类需提供：
    - chunk(parsed, config): 将 ParsedDocument 切分为 ChunkDraft 列表
    - name(): 策略标识（fixed / sentence / recursive）
    """

    async def chunk(self, parsed: ParsedDocument, config: ChunkConfig) -> list[ChunkDraft]:
        """将解析文档切分为分块草稿。

        Args:
            parsed: 解析后的文档（含 sections 与全文）
            config: 分块配置（chunk_size / overlap / separators）

        Returns:
            ChunkDraft 列表，每个含 content / chunk_index / metadata
        """
        ...

    def name(self) -> str:
        """策略标识（fixed / sentence / recursive）。"""
        ...


__all__ = ["BaseChunker"]
