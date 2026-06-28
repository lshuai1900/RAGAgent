"""TXT 文档解析器。

读取纯文本文件，不做任何结构化解析，整篇作为一个 section。
支持 .txt 扩展名。空文件返回空 ParsedDocument。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ragent.domain.dto import ParsedDocument, Section
from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)


class TxtParser:
    """TXT 文档解析器。

    纯文本无结构，整篇作为一个 section（page=None, heading=None）。
    文件读取通过 asyncio.to_thread 包装，避免阻塞事件循环。
    """

    SUPPORTED_TYPES = ["txt"]

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """解析 TXT 文件。

        Args:
            file_path: 文件路径
            file_type: 应为 "txt"

        Returns:
            ParsedDocument，text 为全文，sections 包含单个 Section

        Raises:
            InfraException: 文件不存在或读取失败
        """
        if not file_path.exists():
            raise InfraException(
                message=f"TXT 文件不存在: {file_path}",
                code=30001,
            )

        _logger.info("txt_parse_start", file_path=str(file_path), file_size=file_path.stat().st_size)

        # 通过 asyncio.to_thread 包装同步 IO，避免阻塞事件循环
        text = await asyncio.to_thread(self._read_text, file_path)

        section = Section(content=text, page=None, heading=None)
        metadata = {
            "file_type": "txt",
            "file_name": file_path.name,
            "char_count": len(text),
        }

        _logger.info(
            "txt_parse_done",
            file_path=str(file_path),
            char_count=len(text),
        )
        return ParsedDocument(text=text, sections=[section], metadata=metadata)

    @staticmethod
    def _read_text(file_path: Path) -> str:
        """同步读取文本（UTF-8 优先，失败时尝试 GBK 兜底）。"""
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            _logger.warning("txt_decode_fallback_gbk", file_path=str(file_path))
            return file_path.read_text(encoding="gbk", errors="replace")

    def supported_types(self) -> list[str]:
        """支持的文件类型。"""
        return list(self.SUPPORTED_TYPES)


__all__ = ["TxtParser"]
