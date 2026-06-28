"""PDF 文档解析器。

使用 pypdf 提取文本，按页切分 section，保留 page 元信息。
支持 .pdf 扩展名。空 PDF / 无文本 PDF 返回空 ParsedDocument。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ragent.domain.dto import ParsedDocument, Section
from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)


class PdfParser:
    """PDF 文档解析器。

    使用 pypdf 逐页提取文本，每页对应一个 Section（page=页码, heading=None）。
    pypdf 为同步库，通过 asyncio.to_thread 包装避免阻塞事件循环。
    """

    SUPPORTED_TYPES = ["pdf"]

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """解析 PDF 文件。

        Args:
            file_path: 文件路径
            file_type: 应为 "pdf"

        Returns:
            ParsedDocument，sections 按页切分，每个 section 含 page 元信息

        Raises:
            InfraException: 文件不存在或解析失败
        """
        if not file_path.exists():
            raise InfraException(
                message=f"PDF 文件不存在: {file_path}",
                code=30003,
            )

        _logger.info("pdf_parse_start", file_path=str(file_path), file_size=file_path.stat().st_size)

        # pypdf 是同步库，通过 to_thread 包装避免阻塞事件循环
        pages_text, total_pages = await asyncio.to_thread(self._extract_pages, file_path)

        sections: list[Section] = []
        full_text_parts: list[str] = []
        for page_num, page_text in pages_text:
            if page_text.strip():  # 跳过纯空白页
                sections.append(
                    Section(content=page_text, page=page_num, heading=None)
                )
                full_text_parts.append(page_text)

        full_text = "\n\n".join(full_text_parts)
        metadata = {
            "file_type": "pdf",
            "file_name": file_path.name,
            "char_count": len(full_text),
            "page_count": total_pages,
            "section_count": len(sections),
        }

        _logger.info(
            "pdf_parse_done",
            file_path=str(file_path),
            char_count=len(full_text),
            page_count=total_pages,
            section_count=len(sections),
        )
        return ParsedDocument(text=full_text, sections=sections, metadata=metadata)

    @staticmethod
    def _extract_pages(file_path: Path) -> tuple[list[tuple[int, str]], int]:
        """同步提取 PDF 各页文本。

        Returns:
            (pages, total_pages)：
              - pages: [(page_num, page_text), ...]，page_num 从 1 开始
              - total_pages: PDF 总页数

        Raises:
            InfraException: PDF 解析失败
        """
        try:
            # 延迟导入，避免在模块加载时引入 pypdf
            from pypdf import PdfReader
        except ImportError as exc:
            raise InfraException(
                message="pypdf 未安装，无法解析 PDF",
                code=30004,
                cause=exc,
            ) from exc

        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)
            pages: list[tuple[int, str]] = []
            for i, page in enumerate(reader.pages):
                # 页码从 1 开始（与人类阅读习惯一致）
                page_text = page.extract_text() or ""
                pages.append((i + 1, page_text))
            return pages, total_pages
        except Exception as exc:
            raise InfraException(
                message=f"PDF 解析失败: {file_path.name} - {exc}",
                code=30005,
                cause=exc,
            ) from exc

    def supported_types(self) -> list[str]:
        """支持的文件类型。"""
        return list(self.SUPPORTED_TYPES)


__all__ = ["PdfParser"]
