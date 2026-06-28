"""T5 文档解析器单元测试。

覆盖：
- 空文件
- 超长文件
- 正常 TXT
- 正常 Markdown
- 正常 PDF（生成最小 PDF）
- registry 路由
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ragent.domain.dto import ParsedDocument
from ragent.framework.core.exceptions import BizException, InfraException
from ragent.ingestion.parser.base import BaseDocumentParser
from ragent.ingestion.parser.markdown import MarkdownParser
from ragent.ingestion.parser.pdf import PdfParser
from ragent.ingestion.parser.registry import (
    ParserRegistry,
    get_default_registry,
    get_parser,
)
from ragent.ingestion.parser.txt import TxtParser

# ---------- TxtParser ----------


@pytest.mark.asyncio
async def test_txt_parse_normal(tmp_path: Path) -> None:
    """正常 TXT 文件解析：text 与 sections 正确。"""
    file_path = tmp_path / "demo.txt"
    file_path.write_text("Hello Ragent-Py\n中文测试", encoding="utf-8")

    parser = TxtParser()
    parsed = await parser.parse(file_path, "txt")

    assert isinstance(parsed, ParsedDocument)
    assert "Hello Ragent-Py" in parsed.text
    assert "中文测试" in parsed.text
    assert len(parsed.sections) == 1
    assert parsed.sections[0].content == parsed.text
    assert parsed.sections[0].page is None
    assert parsed.sections[0].heading is None
    assert parsed.metadata["file_type"] == "txt"
    assert parsed.metadata["char_count"] == len(parsed.text)


@pytest.mark.asyncio
async def test_txt_parse_empty_file(tmp_path: Path) -> None:
    """空 TXT 文件：text 为空字符串，sections 含一个空 section。"""
    file_path = tmp_path / "empty.txt"
    file_path.write_text("", encoding="utf-8")

    parser = TxtParser()
    parsed = await parser.parse(file_path, "txt")

    assert parsed.text == ""
    assert len(parsed.sections) == 1
    assert parsed.sections[0].content == ""
    assert parsed.metadata["char_count"] == 0


@pytest.mark.asyncio
async def test_txt_parse_long_file(tmp_path: Path) -> None:
    """超长 TXT 文件：完整读取不截断。"""
    file_path = tmp_path / "long.txt"
    content = "abcdefghij" * 10000  # 100,000 字符
    file_path.write_text(content, encoding="utf-8")

    parser = TxtParser()
    parsed = await parser.parse(file_path, "txt")

    assert len(parsed.text) == 100000
    assert parsed.metadata["char_count"] == 100000


@pytest.mark.asyncio
async def test_txt_parse_gbk_fallback(tmp_path: Path) -> None:
    """GBK 编码 TXT：UTF-8 解码失败时回退 GBK。"""
    file_path = tmp_path / "gbk.txt"
    file_path.write_bytes("中文内容".encode("gbk"))

    parser = TxtParser()
    parsed = await parser.parse(file_path, "txt")

    assert "中文内容" in parsed.text


@pytest.mark.asyncio
async def test_txt_parse_file_not_exists(tmp_path: Path) -> None:
    """文件不存在：抛 InfraException。"""
    parser = TxtParser()
    with pytest.raises(InfraException) as exc_info:
        await parser.parse(tmp_path / "no_such.txt", "txt")
    assert exc_info.value.code == 30001


def test_txt_supported_types() -> None:
    """supported_types 返回 ['txt']。"""
    assert TxtParser().supported_types() == ["txt"]


# ---------- MarkdownParser ----------


@pytest.mark.asyncio
async def test_md_parse_normal(tmp_path: Path) -> None:
    """正常 Markdown：按 ATX 标题切分 section。"""
    file_path = tmp_path / "demo.md"
    file_path.write_text(
        "# 标题一\n内容一\n\n## 标题二\n内容二\n",
        encoding="utf-8",
    )

    parser = MarkdownParser()
    parsed = await parser.parse(file_path, "md")

    assert "标题一" in parsed.text
    assert "内容一" in parsed.text
    # 至少 2 个 section（标题一、标题二）
    assert len(parsed.sections) >= 2
    headings = [s.heading for s in parsed.sections if s.heading]
    assert "标题一" in headings
    assert "标题二" in headings
    assert parsed.metadata["file_type"] == "md"
    assert parsed.metadata["section_count"] == len(parsed.sections)


@pytest.mark.asyncio
async def test_md_parse_no_heading(tmp_path: Path) -> None:
    """无标题 Markdown：整篇作为单 section。"""
    file_path = tmp_path / "noheading.md"
    file_path.write_text("纯文本内容，无标题。", encoding="utf-8")

    parser = MarkdownParser()
    parsed = await parser.parse(file_path, "md")

    assert len(parsed.sections) == 1
    assert parsed.sections[0].heading is None
    assert parsed.sections[0].content == "纯文本内容，无标题。"


@pytest.mark.asyncio
async def test_md_parse_empty_file(tmp_path: Path) -> None:
    """空 Markdown 文件：sections 为空。"""
    file_path = tmp_path / "empty.md"
    file_path.write_text("", encoding="utf-8")

    parser = MarkdownParser()
    parsed = await parser.parse(file_path, "md")

    assert parsed.text == ""
    assert parsed.sections == []
    assert parsed.metadata["section_count"] == 0


@pytest.mark.asyncio
async def test_md_parse_file_not_exists(tmp_path: Path) -> None:
    """文件不存在：抛 InfraException。"""
    parser = MarkdownParser()
    with pytest.raises(InfraException) as exc_info:
        await parser.parse(tmp_path / "no_such.md", "md")
    assert exc_info.value.code == 30002


def test_md_supported_types() -> None:
    """supported_types 返回 ['md', 'markdown']。"""
    types = MarkdownParser().supported_types()
    assert "md" in types
    assert "markdown" in types


# ---------- PdfParser ----------


@pytest.mark.asyncio
async def test_pdf_parse_normal(tmp_path: Path) -> None:
    """正常 PDF：保留 page 元信息。"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab 未安装，跳过 PDF 生成测试")

    file_path = tmp_path / "demo.pdf"
    c = canvas.Canvas(str(file_path), pagesize=A4)
    c.drawString(100, 750, "Page 1 content")
    c.showPage()
    c.drawString(100, 750, "Page 2 content")
    c.showPage()
    c.save()

    parser = PdfParser()
    parsed = await parser.parse(file_path, "pdf")

    assert parsed.metadata["file_type"] == "pdf"
    assert parsed.metadata["page_count"] == 2
    assert len(parsed.sections) <= 2  # 可能因空白页减少
    # 每个 section 都应有 page 元信息
    for section in parsed.sections:
        assert section.page is not None
        assert section.page >= 1


@pytest.mark.asyncio
async def test_pdf_parse_file_not_exists(tmp_path: Path) -> None:
    """文件不存在：抛 InfraException。"""
    parser = PdfParser()
    with pytest.raises(InfraException) as exc_info:
        await parser.parse(tmp_path / "no_such.pdf", "pdf")
    assert exc_info.value.code == 30003


def test_pdf_supported_types() -> None:
    """supported_types 返回 ['pdf']。"""
    assert PdfParser().supported_types() == ["pdf"]


# ---------- Registry ----------


def test_registry_default_parsers_registered() -> None:
    """默认注册表已注册 TXT/MD/PDF。"""
    registry = get_default_registry()
    types = registry.supported_types()
    assert "txt" in types
    assert "md" in types
    assert "pdf" in types


def test_registry_get_parser_returns_correct_instance() -> None:
    """按 file_type 路由到对应 parser。"""
    assert isinstance(get_parser("txt"), TxtParser)
    assert isinstance(get_parser("md"), MarkdownParser)
    assert isinstance(get_parser("pdf"), PdfParser)


def test_registry_unsupported_type_raises_biz_exception() -> None:
    """不支持的类型：抛 BizException。"""
    registry = get_default_registry()
    with pytest.raises(BizException) as exc_info:
        registry.get_parser("pptx")
    assert exc_info.value.code == 10101


def test_registry_custom_registration() -> None:
    """自定义注册 parser：动态扩展。"""

    class DummyParser:
        async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
            return ParsedDocument(text="", sections=[], metadata={})

        def supported_types(self) -> list[str]:
            return ["dummy"]

    registry = ParserRegistry()
    registry.register(DummyParser())  # type: ignore[arg-type]
    assert "dummy" in registry.supported_types()
    parser = registry.get_parser("dummy")
    assert isinstance(parser, DummyParser)


# ---------- 协议检查 ----------


def test_all_parsers_implement_base_protocol() -> None:
    """三种 parser 均符合 BaseDocumentParser 协议（runtime_checkable）。"""
    assert isinstance(TxtParser(), BaseDocumentParser)
    assert isinstance(MarkdownParser(), BaseDocumentParser)
    assert isinstance(PdfParser(), BaseDocumentParser)
