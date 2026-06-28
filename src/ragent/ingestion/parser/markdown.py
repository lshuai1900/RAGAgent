"""Markdown 文档解析器。

按 ATX 标题（# / ## / ...）切分章节，保留每个章节的 heading 元信息。
支持 .md 扩展名。空文件返回空 ParsedDocument。
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from ragent.domain.dto import ParsedDocument, Section
from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)

# ATX 标题正则：行首 1-6 个 # 后跟空格，捕获标题文本
_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class MarkdownParser:
    """Markdown 文档解析器。

    按 ATX 标题（# / ## / ...）切分章节。文档开头到第一个标题之间的内容作为
    一个无名 section（heading=None）。后续每个标题对应一个 section。
    """

    SUPPORTED_TYPES = ["md", "markdown"]

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """解析 Markdown 文件。

        Args:
            file_path: 文件路径
            file_type: 应为 "md" 或 "markdown"

        Returns:
            ParsedDocument，sections 按标题切分，每个 section 含 heading

        Raises:
            InfraException: 文件不存在或读取失败
        """
        if not file_path.exists():
            raise InfraException(
                message=f"Markdown 文件不存在: {file_path}",
                code=30002,
            )

        _logger.info("md_parse_start", file_path=str(file_path), file_size=file_path.stat().st_size)

        text = await asyncio.to_thread(self._read_text, file_path)
        sections = self._split_sections(text)

        metadata = {
            "file_type": "md",
            "file_name": file_path.name,
            "char_count": len(text),
            "section_count": len(sections),
        }

        _logger.info(
            "md_parse_done",
            file_path=str(file_path),
            char_count=len(text),
            section_count=len(sections),
        )
        return ParsedDocument(text=text, sections=sections, metadata=metadata)

    @staticmethod
    def _read_text(file_path: Path) -> str:
        """同步读取 Markdown 文本（UTF-8）。"""
        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def _split_sections(text: str) -> list[Section]:
        """按 ATX 标题切分章节。

        切分策略：
        - 找到所有标题行，每个标题到下一个标题之间的内容构成一个 section
        - 文档开头到第一个标题之间的内容作为前置 section（heading=None）
        - 标题文本去除 # 前缀后作为 section.heading
        - 每个 section 的 content 保留原标题行 + 正文，便于分块器获取完整上下文

        Args:
            text: Markdown 全文

        Returns:
            章节列表，无标题时返回单 section（content=全文）
        """
        if not text:
            return []

        matches = list(_HEADING_PATTERN.finditer(text))
        if not matches:
            # 无标题：整篇作为单 section
            return [Section(content=text, page=None, heading=None)]

        sections: list[Section] = []

        # 前置内容（首个标题之前的文本）
        first_start = matches[0].start()
        if first_start > 0:
            prelude = text[:first_start].strip()
            if prelude:
                sections.append(Section(content=prelude, page=None, heading=None))

        # 每个标题对应一个 section
        for i, match in enumerate(matches):
            heading_text = match.group(2).strip()
            content_start = match.start()
            content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_content = text[content_start:content_end].strip()
            if section_content:
                sections.append(
                    Section(content=section_content, page=None, heading=heading_text)
                )

        return sections

    def supported_types(self) -> list[str]:
        """支持的文件类型。"""
        return list(self.SUPPORTED_TYPES)


__all__ = ["MarkdownParser"]
