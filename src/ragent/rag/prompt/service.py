"""Prompt 模板服务：加载与渲染 configs/prompts/ 下的模板文件。

约束：
- 模板必须放在 configs/prompts/，禁止在代码内硬编码长 Prompt
- 占位符格式：{key}（如 {evidence} / {question} / {history}）
- 禁止使用 Jinja2 语法（MVP 用简单 {key} 占位符 + str.format_map）
- 模板内容缓存（避免每次 IO 读文件）

PromptService 不依赖 persistence / infra_ai / api，仅依赖 framework（用于路径解析）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ragent.framework.core.exceptions import SysException
from ragent.framework.core.logging import get_logger

_logger = get_logger(__name__)

# 项目根目录（pyproject.toml 所在目录）
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_PROMPTS_DIR = _PROJECT_ROOT / "configs" / "prompts"

# 模板文件名常量
TEMPLATE_ANSWER_CHAT_KB = "answer-chat-kb.txt"
TEMPLATE_CONTEXT_FORMAT = "context-format.txt"


class PromptService:
    """Prompt 模板服务。

    职责：
    - 加载 configs/prompts/*.txt 模板文件
    - 用 {key} 占位符渲染（str.format_map）
    - 缓存模板内容（避免重复 IO）

    不依赖 persistence / infra_ai / api。
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        """初始化 PromptService。

        Args:
            prompts_dir: 模板目录，None 时默认 configs/prompts/
        """
        self._prompts_dir = prompts_dir or _PROMPTS_DIR
        self._cache: dict[str, str] = {}

    def render(self, template_name: str, **kwargs: Any) -> str:
        """渲染指定模板。

        用 str.format_map 替换 {key} 占位符。缺失的 key 保留原样（不报错）。

        Args:
            template_name: 模板文件名（如 "answer-chat-kb.txt"）
            **kwargs: 占位符键值对

        Returns:
            渲染后的字符串

        Raises:
            SysException: 模板文件不存在或读取失败
        """
        template = self._load_template(template_name)
        # 用 SafeDict 避免缺失 key 抛 KeyError（保留原占位符）
        return template.format_map(_SafeDict(kwargs))

    def render_answer_chat_kb(
        self,
        *,
        evidence: str,
        question: str,
        history: str = "",
    ) -> str:
        """渲染 KB 问答模板（便捷方法）。

        Args:
            evidence: 检索证据上下文（已格式化）
            question: 用户问题
            history: 历史对话（可空）

        Returns:
            渲染后的 Prompt
        """
        return self.render(
            TEMPLATE_ANSWER_CHAT_KB,
            evidence=evidence,
            question=question,
            history=history,
        )

    def render_context_format(self, *, evidence_items: str) -> str:
        """渲染上下文格式化模板（便捷方法）。

        Args:
            evidence_items: 已格式化的证据条目列表（拼接后的字符串）

        Returns:
            渲染后的上下文文本
        """
        return self.render(
            TEMPLATE_CONTEXT_FORMAT,
            evidence_items=evidence_items,
        )

    def format_evidence_items(
        self,
        items: list[str],
        *,
        separator: str = "\n\n",
    ) -> str:
        """把证据条目列表格式化为单个字符串。

        每条前加 [i] 编号，便于 LLM 引用来源。

        Args:
            items: 证据文本列表
            separator: 条目分隔符

        Returns:
            格式化后的证据字符串
        """
        if not items:
            return ""
        numbered = [f"[{i + 1}] {item}" for i, item in enumerate(items)]
        return separator.join(numbered)

    def _load_template(self, template_name: str) -> str:
        """加载模板文件（带缓存）。

        Args:
            template_name: 模板文件名

        Returns:
            模板文本

        Raises:
            SysException: 文件不存在或读取失败
        """
        if template_name in self._cache:
            return self._cache[template_name]

        path = self._prompts_dir / template_name
        if not path.exists():
            raise SysException(
                message=f"Prompt 模板不存在: {path}",
                code=20101,
            )
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SysException(
                message=f"Prompt 模板读取失败: {path} - {exc}",
                code=20102,
                cause=exc,
            ) from exc

        self._cache[template_name] = content
        _logger.debug("prompt_template_loaded", template=template_name, length=len(content))
        return content


class _SafeDict(dict[str, str]):
    """format_map 的安全字典：缺失 key 时返回原占位符 {key}，不抛 KeyError。"""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


__all__ = [
    "TEMPLATE_ANSWER_CHAT_KB",
    "TEMPLATE_CONTEXT_FORMAT",
    "PromptService",
]
