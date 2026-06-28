"""文档解析抽象接口。

BaseDocumentParser 只依赖 domain.dto.ParsedDocument，禁止依赖 persistence / infra_ai / rag / api。
实现类（TxtParser/MarkdownParser/PdfParser）放在同包具体文件，
通过 ingestion/parser/registry.py 注册并按 file_type 路由。
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ragent.domain.dto import ParsedDocument


@runtime_checkable
class BaseDocumentParser(Protocol):
    """文档解析抽象接口。

    实现类需提供：
    - parse(file_path, file_type): 将文件解析为 ParsedDocument
    - supported_types(): 声明支持的文件类型（不含点，如 "txt" / "md" / "pdf"）
    """

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """将文件解析为结构化文档。

        Args:
            file_path: 文件绝对路径
            file_type: 文件类型（不含点，小写）

        Returns:
            ParsedDocument，含全文文本、章节结构、文档级元信息
        """
        ...

    def supported_types(self) -> list[str]:
        """声明支持的文件类型（不含点，小写）。

        Returns:
            支持的文件类型列表，如 ["txt"] / ["md"] / ["pdf"]
        """
        ...


__all__ = ["BaseDocumentParser"]
