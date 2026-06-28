"""T12 PromptService 单元测试。

约束：
- 不依赖外部服务
- 覆盖：
  - render 基本占位符替换
  - render 缺失 key 保留原占位符（不抛 KeyError）
  - render_answer_chat_kb 便捷方法
  - render_context_format 便捷方法
  - format_evidence_items 编号格式
  - 模板缓存（重复调用不重复 IO）
  - 模板不存在抛 SysException
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ragent.framework.core.exceptions import SysException
from ragent.rag.prompt.service import (
    TEMPLATE_ANSWER_CHAT_KB,
    TEMPLATE_CONTEXT_FORMAT,
    PromptService,
)

# ---------- 临时模板目录 fixture ----------


@pytest.fixture
def tmp_prompts_dir(tmp_path: Path) -> Path:
    """构造临时模板目录，写入测试用模板。"""
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "answer-chat-kb.txt").write_text(
        "System: 请基于证据回答。\n\n<evidence>\n{evidence}\n</evidence>\n\n"
        "<history>\n{history}\n</history>\n\n问题：{question}\n",
        encoding="utf-8",
    )
    (prompts / "context-format.txt").write_text(
        "相关上下文：\n{evidence_items}\n",
        encoding="utf-8",
    )
    # 额外测试模板
    (prompts / "simple.txt").write_text(
        "Hello {name}, your score is {score}.",
        encoding="utf-8",
    )
    return prompts


# ---------- render 基本功能 ----------


def test_render_replaces_placeholders(tmp_prompts_dir: Path) -> None:
    """render 正确替换所有占位符。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    out = service.render("simple.txt", name="Alice", score="95")
    assert out == "Hello Alice, your score is 95."


def test_render_missing_key_preserves_placeholder(tmp_prompts_dir: Path) -> None:
    """render 缺失 key 时保留原占位符（不抛 KeyError）。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    out = service.render("simple.txt", name="Bob")  # 缺 score
    assert out == "Hello Bob, your score is {score}."


def test_render_template_cached(tmp_prompts_dir: Path) -> None:
    """模板首次加载后缓存，重复调用不重复 IO。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    # 首次加载
    out1 = service.render("simple.txt", name="A", score="1")
    # 修改文件内容（模拟缓存生效：第二次仍应读到首次内容）
    (tmp_prompts_dir / "simple.txt").write_text("CHANGED {name}", encoding="utf-8")
    out2 = service.render("simple.txt", name="A", score="1")
    assert out1 == out2
    assert "CHANGED" not in out2


def test_render_template_not_found_raises(tmp_prompts_dir: Path) -> None:
    """模板不存在：抛 SysException(20101)。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    with pytest.raises(SysException) as exc_info:
        service.render("non-existent.txt")
    assert exc_info.value.code == 20101


def test_render_uses_default_prompts_dir() -> None:
    """默认 prompts_dir 指向 configs/prompts/。"""
    service = PromptService()
    # 加载真实模板（项目根 configs/prompts/answer-chat-kb.txt）
    out = service.render_answer_chat_kb(
        evidence="测试证据",
        question="测试问题",
        history="",
    )
    assert "测试证据" in out
    assert "测试问题" in out


# ---------- render_answer_chat_kb ----------


def test_render_answer_chat_kb(tmp_prompts_dir: Path) -> None:
    """render_answer_chat_kb 正确渲染 KB 问答模板。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    out = service.render_answer_chat_kb(
        evidence="证据1",
        question="问题1",
        history="历史1",
    )
    assert "证据1" in out
    assert "问题1" in out
    assert "历史1" in out


def test_render_answer_chat_kb_default_history(tmp_prompts_dir: Path) -> None:
    """history 默认空字符串。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    out = service.render_answer_chat_kb(evidence="E", question="Q")
    # history 占位符被替换为空
    assert "{history}" not in out


# ---------- render_context_format ----------


def test_render_context_format(tmp_prompts_dir: Path) -> None:
    """render_context_format 正确渲染。"""
    service = PromptService(prompts_dir=tmp_prompts_dir)
    out = service.render_context_format(evidence_items="条目1\n条目2")
    assert "条目1\n条目2" in out


# ---------- format_evidence_items ----------


def test_format_evidence_items_numbered() -> None:
    """format_evidence_items 给每条加 [i] 编号。"""
    service = PromptService()
    out = service.format_evidence_items(["A", "B", "C"])
    assert "[1] A" in out
    assert "[2] B" in out
    assert "[3] C" in out


def test_format_evidence_items_empty() -> None:
    """空列表返回空字符串。"""
    service = PromptService()
    assert service.format_evidence_items([]) == ""


def test_format_evidence_items_custom_separator() -> None:
    """自定义分隔符。"""
    service = PromptService()
    out = service.format_evidence_items(["X", "Y"], separator=" | ")
    assert " | " in out
    assert "[1] X" in out
    assert "[2] Y" in out


# ---------- 模板常量 ----------


def test_template_constants() -> None:
    """模板文件名常量正确。"""
    assert TEMPLATE_ANSWER_CHAT_KB == "answer-chat-kb.txt"
    assert TEMPLATE_CONTEXT_FORMAT == "context-format.txt"
