"""固定大小分块器。

按 chunk_size 字符切分，相邻块通过 overlap 字符重叠。
不识别任何语义边界，仅按字符数机械切分。

适用于：纯文本、无明显段落结构的文档。
"""

from __future__ import annotations

from ragent.domain.dto import ChunkDraft, ParsedDocument, Section
from ragent.domain.value_objects import ChunkConfig
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)


class FixedSizeChunker:
    """固定大小分块器。

    切分策略：
    - 按 section 顺序处理，每个 section 独立切分
    - 单块最大 chunk_size 字符，相邻块通过 overlap 字符重叠
    - 每个 chunk 的 metadata 含来源 section 的 page / heading
    - chunk_index 在整篇文档内全局递增（从 0 开始）
    """

    async def chunk(self, parsed: ParsedDocument, config: ChunkConfig) -> list[ChunkDraft]:
        """按固定大小切分文档。

        Args:
            parsed: 解析后的文档
            config: 分块配置（使用 chunk_size 与 overlap）

        Returns:
            ChunkDraft 列表，空文档返回空列表
        """
        if config.chunk_size <= 0:
            raise ValueError(f"chunk_size 必须为正数，当前: {config.chunk_size}")
        if config.overlap < 0:
            raise ValueError(f"overlap 不能为负数，当前: {config.overlap}")
        if config.overlap >= config.chunk_size:
            raise ValueError(
                f"overlap 必须小于 chunk_size，当前 overlap={config.overlap} chunk_size={config.chunk_size}"
            )

        sections = parsed.sections or [Section(content=parsed.text, page=None, heading=None)]
        chunks: list[ChunkDraft] = []
        global_index = 0

        for section in sections:
            text = section.content
            if not text:
                continue
            section_chunks = self._split_fixed(text, config)
            for chunk_text in section_chunks:
                if not chunk_text.strip():
                    continue
                metadata = {
                    "page": section.page,
                    "heading": section.heading,
                    "char_count": len(chunk_text),
                    "chunker": "fixed",
                }
                chunks.append(
                    ChunkDraft(
                        content=chunk_text,
                        chunk_index=global_index,
                        metadata=metadata,
                    )
                )
                global_index += 1

        _logger.info(
            "fixed_chunk_done",
            chunk_count=len(chunks),
            chunk_size=config.chunk_size,
            overlap=config.overlap,
        )
        return chunks

    @staticmethod
    def _split_fixed(text: str, config: ChunkConfig) -> list[str]:
        """按固定大小 + overlap 切分单段文本。

        切分逻辑：
        - 起始位置 i 从 0 开始
        - 块范围 [i, i+chunk_size)
        - 下一块起始 i += (chunk_size - overlap)
        - 直到 i + overlap >= len(text) 停止（最后一段已被覆盖）

        Args:
            text: 待切分文本
            config: 分块配置

        Returns:
            切分后的字符串列表
        """
        size = config.chunk_size
        overlap = config.overlap
        text_len = len(text)

        if text_len <= size:
            return [text] if text else []

        step = size - overlap
        chunks: list[str] = []
        i = 0
        while i < text_len:
            chunk_end = min(i + size, text_len)
            chunks.append(text[i:chunk_end])
            if chunk_end >= text_len:
                break
            i += step
        return chunks

    def name(self) -> str:
        """策略标识。"""
        return "fixed"


__all__ = ["FixedSizeChunker"]
