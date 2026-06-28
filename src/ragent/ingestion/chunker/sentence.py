"""句子分块器。

按句子边界（。！？.!? 等）切分，尽量在句子边界处断开。
单块不超过 chunk_size 字符，相邻块通过 overlap 字符重叠。

适用于：自然语言文档（中文/英文混排）。
"""

from __future__ import annotations

import re

from ragent.domain.dto import ChunkDraft, ParsedDocument, Section
from ragent.domain.value_objects import ChunkConfig
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)

# 句子结束符：中英文句号/问号/感叹号 + 换行
# 保留分隔符在句子末尾
_SENTENCE_PATTERN = re.compile(r"(?<=[。！？.!?])\s*|\n+")


class SentenceChunker:
    """句子分块器。

    切分策略：
    - 先按句子边界切分文本为句子列表
    - 顺序累积句子，累积长度超过 chunk_size 时断开
    - overlap 通过保留前一块末尾若干句子实现
    - 每个 chunk 的 metadata 含来源 section 的 page / heading
    """

    async def chunk(self, parsed: ParsedDocument, config: ChunkConfig) -> list[ChunkDraft]:
        """按句子边界切分文档。

        Args:
            parsed: 解析后的文档
            config: 分块配置

        Returns:
            ChunkDraft 列表，空文档返回空列表
        """
        if config.chunk_size <= 0:
            raise ValueError(f"chunk_size 必须为正数，当前: {config.chunk_size}")
        if config.overlap < 0:
            raise ValueError(f"overlap 不能为负数，当前: {config.overlap}")

        sections = parsed.sections or [Section(content=parsed.text, page=None, heading=None)]
        chunks: list[ChunkDraft] = []
        global_index = 0

        for section in sections:
            text = section.content
            if not text:
                continue
            section_chunks = self._split_sentences(text, config)
            for chunk_text in section_chunks:
                if not chunk_text.strip():
                    continue
                metadata = {
                    "page": section.page,
                    "heading": section.heading,
                    "char_count": len(chunk_text),
                    "chunker": "sentence",
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
            "sentence_chunk_done",
            chunk_count=len(chunks),
            chunk_size=config.chunk_size,
            overlap=config.overlap,
        )
        return chunks

    @staticmethod
    def _split_sentences(text: str, config: ChunkConfig) -> list[str]:
        """按句子边界 + chunk_size + overlap 切分单段文本。

        策略：
        1. 用正则把文本切为句子列表（保留分隔符）
        2. 累积句子，累积长度 > chunk_size 时发出一个 chunk
        3. 下一个 chunk 起始 = 前一个 chunk 的末尾 overlap 字符

        Args:
            text: 待切分文本
            config: 分块配置

        Returns:
            切分后的字符串列表
        """
        if not text:
            return []

        # 切分为句子（保留分隔符在句尾）
        sentences = _SENTENCE_PATTERN.split(text)
        sentences = [s for s in sentences if s]

        if not sentences:
            return []

        size = config.chunk_size
        overlap = config.overlap

        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for sentence in sentences:
            # 单句超长时强制按 chunk_size 切分（避免一个 chunk 远超限制）
            if len(sentence) > size:
                # 先发出已累积的部分
                if current_parts:
                    chunks.append("".join(current_parts))
                    current_parts = []
                    current_len = 0
                # 再把超长句按 chunk_size 切分
                for i in range(0, len(sentence), size):
                    chunks.append(sentence[i : i + size])
                continue

            if current_len + len(sentence) > size and current_parts:
                # 当前累积已满，发出 chunk
                chunk_text = "".join(current_parts)
                chunks.append(chunk_text)
                # 计算 overlap：保留前一块末尾 overlap 字符作为下一块开头
                if overlap > 0 and len(chunk_text) > overlap:
                    tail = chunk_text[-overlap:]
                    current_parts = [tail]
                    current_len = len(tail)
                else:
                    current_parts = []
                    current_len = 0

            current_parts.append(sentence)
            current_len += len(sentence)

        # 发出剩余部分
        if current_parts:
            remaining = "".join(current_parts)
            if remaining.strip():
                chunks.append(remaining)

        return chunks

    def name(self) -> str:
        """策略标识。"""
        return "sentence"


__all__ = ["SentenceChunker"]
