"""文档解析器注册表。

按 file_type 路由到对应的 BaseDocumentParser 实现。
启动时注册默认实现（TxtParser / MarkdownParser / PdfParser）。
业务代码（service / pipeline）通过 get_parser(file_type) 获取实现，不直接依赖具体类。
"""

from __future__ import annotations

from ragent.framework.core.exceptions import BizException
from ragent.framework.core.logging import get_logger
from ragent.ingestion.parser.base import BaseDocumentParser
from ragent.ingestion.parser.markdown import MarkdownParser
from ragent.ingestion.parser.pdf import PdfParser
from ragent.ingestion.parser.txt import TxtParser

_logger = get_logger(__name__)


class ParserRegistry:
    """文档解析器注册表。

    按 file_type（不含点，小写）注册并路由 parser 实现。
    支持动态注册新 parser（扩展点），不修改既有调用代码。
    """

    def __init__(self) -> None:
        self._parsers: dict[str, BaseDocumentParser] = {}

    def register(self, parser: BaseDocumentParser) -> None:
        """注册 parser，按其 supported_types 自动建立 file_type → parser 映射。

        Args:
            parser: 实现 BaseDocumentParser 的实例
        """
        for file_type in parser.supported_types():
            normalized = file_type.lower().lstrip(".")
            self._parsers[normalized] = parser
            _logger.info(
                "parser_registered",
                file_type=normalized,
                parser=parser.__class__.__name__,
            )

    def get_parser(self, file_type: str) -> BaseDocumentParser:
        """按 file_type 获取 parser。

        Args:
            file_type: 文件类型（不含点，大小写不敏感）

        Returns:
            对应的 BaseDocumentParser 实现

        Raises:
            BizException: 不支持的文件类型
        """
        normalized = file_type.lower().lstrip(".")
        parser = self._parsers.get(normalized)
        if parser is None:
            supported = sorted(self._parsers.keys())
            raise BizException(
                message=(f"不支持的文件类型: {file_type}，当前支持的类型: {supported}"),
                code=10101,
            )
        return parser

    def supported_types(self) -> list[str]:
        """返回当前注册的所有 file_type。"""
        return sorted(self._parsers.keys())


# 模块级默认注册表：启动时注册 MVP 支持的三种 parser
_default_registry = ParserRegistry()
_default_registry.register(TxtParser())
_default_registry.register(MarkdownParser())
_default_registry.register(PdfParser())


def get_default_registry() -> ParserRegistry:
    """获取默认注册表单例（含 MVP 已注册的 TXT/MD/PDF parser）。"""
    return _default_registry


def get_parser(file_type: str) -> BaseDocumentParser:
    """便捷函数：从默认注册表获取 parser。"""
    return _default_registry.get_parser(file_type)


__all__ = [
    "ParserRegistry",
    "get_default_registry",
    "get_parser",
]
