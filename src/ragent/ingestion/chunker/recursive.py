"""递归分块器（默认策略）。

按分隔符优先级递归切分，尽量在最高优先级分隔符处断开，
无法切分时降级到次优先级分隔符，直到达到 chunk_size。

借鉴 LangChain RecursiveCharacterTextSplitter 的思想但简化实现。

适用于：多数文档（混合结构 + 自然语言）。
"""

from __future__ import annotations

from ragent.domain.dto import ChunkDraft, ParsedDocument, Section
from ragent.domain.value_objects import ChunkConfig
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)

# 默认分隔符优先级（从高到低）：
# 段落分隔 → 换行 → 中文句号 → 中文问号/感叹号 → 英文句号 → 英文问号/感叹号 → 空格 → 空字符串
DEFAULT_SEPARATORS: list[str] = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    ".",
    "!",
    "?",
    " ",
    "",
]


class RecursiveChunker:
    """递归分块器（默认策略）。

    切分策略：
    - 按 section 顺序处理
    - 对每个 section 的文本，按 separators 优先级递归切分
    - 累积切分后的子串到 chunk_size，相邻块通过 overlap 字符重叠
    - 每个 chunk 的 metadata 含来源 section 的 page / heading
    """

    async def chunk(self, parsed: ParsedDocument, config: ChunkConfig) -> list[ChunkDraft]:
        """按递归分隔符切分文档。

        Args:
            parsed: 解析后的文档
            config: 分块配置（chunk_size / overlap / separators）

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

        separators = config.separators if config.separators else list(DEFAULT_SEPARATORS)
        sections = parsed.sections or [Section(content=parsed.text, page=None, heading=None)]

        chunks: list[ChunkDraft] = []
        global_index = 0

        for section in sections:
            text = section.content
            if not text:
                continue
            # 递归切分到 chunk_size 以下的小段
            splits = self._recursive_split(text, separators, config.chunk_size)
            # 累积小段为 chunk，带 overlap
            section_chunks = self._merge_splits(splits, config)
            for chunk_text in section_chunks:
                if not chunk_text.strip():
                    continue
                metadata = {
                    "page": section.page,
                    "heading": section.heading,
                    "char_count": len(chunk_text),
                    "chunker": "recursive",
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
            "recursive_chunk_done",
            chunk_count=len(chunks),
            chunk_size=config.chunk_size,
            overlap=config.overlap,
        )
        return chunks

    @classmethod
    def _recursive_split(
        cls,
        text: str,
        separators: list[str],
        chunk_size: int,
    ) -> list[str]:
        """递归按分隔符优先级切分文本。

        策略：
        - 找到第一个能切分文本的分隔符（separators 按优先级排序）
        - 用该分隔符切分，得到子段列表
        - 对每个子段：若长度 <= chunk_size，保留；否则用下一个分隔符继续切分
        - 若所有分隔符都无法切分（最末为空字符串），强制按 chunk_size 切分

        Args:
            text: 待切分文本
            separators: 分隔符优先级列表
            chunk_size: 单块最大字符数

        Returns:
            切分后的子段列表（每个子段长度 <= chunk_size，除非单字符长且无分隔符）
        """
        if len(text) <= chunk_size:
            return [text] if text else []

        for idx, sep in enumerate(separators):
            if sep == "":
                # 空字符串分隔符：强制按 chunk_size 切分
                break

            if sep not in text:
                continue

            # 用当前分隔符切分（保留分隔符在子段末尾，避免语义断裂）
            parts = text.split(sep)
            splits: list[str] = []
            for part in parts:
                if part:
                    # 重新加上分隔符（除最后一段外）
                    candidate = part + sep
                else:
                    continue

                if len(candidate) <= chunk_size:
                    splits.append(candidate)
                else:
                    # 子段仍超长，递归用更次级的分隔符切分
                    sub_separators = separators[idx + 1 :]
                    splits.extend(cls._recursive_split(candidate, sub_separators, chunk_size))

            # 合并相邻可合并的小段（避免切碎）
            return cls._merge_adjacent(splits, chunk_size)

        # 所有分隔符都无法切分：强制按 chunk_size 切分
        return cls._force_split(text, chunk_size)

    @staticmethod
    def _merge_adjacent(splits: list[str], chunk_size: int) -> list[str]:
        """合并相邻的小段，使每段尽量接近 chunk_size 但不超过。

        Args:
            splits: 切分后的子段列表
            chunk_size: 单块最大字符数

        Returns:
            合并后的子段列表
        """
        if not splits:
            return []

        merged: list[str] = []
        current = ""
        for part in splits:
            if not part:
                continue
            if len(current) + len(part) <= chunk_size:
                current += part
            else:
                if current:
                    merged.append(current)
                current = part
        if current:
            merged.append(current)
        return merged

    @staticmethod
    def _force_split(text: str, chunk_size: int) -> list[str]:
        """无法用分隔符切分时，强制按字符数切分。

        Args:
            text: 待切分文本
            chunk_size: 单块最大字符数

        Returns:
            切分后的字符串列表
        """
        if not text:
            return []
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    @classmethod
    def _merge_splits(cls, splits: list[str], config: ChunkConfig) -> list[str]:
        """把递归切分得到的小段合并为带 overlap 的 chunk。

        策略：
        - 顺序累积 splits，累积长度 > chunk_size 时发出 chunk
        - 下一个 chunk 起始 = 前一个 chunk 的末尾 overlap 字符

        Args:
            splits: 递归切分得到的小段列表
            config: 分块配置

        Returns:
            chunk 文本列表
        """
        if not splits:
            return []

        size = config.chunk_size
        overlap = config.overlap

        chunks: list[str] = []
        current = ""

        for part in splits:
            if not part:
                continue

            # 当前块加上 part 后超长，且当前块非空：发出当前块
            if len(current) + len(part) > size and current:
                chunks.append(current)
                # overlap：保留前一块末尾 overlap 字符
                current = current[-overlap:] if overlap > 0 and len(current) > overlap else ""

            # 若 part 自身超长（不应发生，但兜底），强制切分
            if len(part) > size:
                # 先把 current 发出
                if current:
                    chunks.append(current)
                    current = ""
                # part 按 size 切分
                for i in range(0, len(part), size):
                    chunks.append(part[i : i + size])
                continue

            current += part

        if current.strip():
            chunks.append(current)

        return chunks

    def name(self) -> str:
        """策略标识。"""
        return "recursive"


__all__ = ["DEFAULT_SEPARATORS", "RecursiveChunker"]
