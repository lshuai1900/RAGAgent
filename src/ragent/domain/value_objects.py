"""值对象（dataclass）。

纯领域，零业务依赖。供 ingestion / rag / infra_ai / service 共享。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChunkConfig:
    """分块配置。

    Attributes:
        chunk_size: 单块最大字符数
        overlap: 相邻块重叠字符数（保证上下文连续性）
        separators: 分隔符优先级（recursive 策略按顺序尝试切分）
    """

    chunk_size: int = 512
    overlap: int = 64
    separators: list[str] = field(
        default_factory=lambda: ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
    )


@dataclass
class ChatOptions:
    """对话选项（第三批使用）。

    Attributes:
        temperature: 采样温度，0.0 表示最确定输出
        top_p: nucleus sampling 概率截断
        max_tokens: 最大输出 token 数
        stop: 停止词列表
    """

    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int | None = None
    stop: list[str] | None = None


@dataclass
class RetrievalQuery:
    """检索查询（第三批使用）。

    Attributes:
        text: 查询文本
        kb_id: 限定的知识库 ID（MVP 单 KB，必填）
        session_id: 关联会话 ID（用于记忆场景，可空）
    """

    text: str
    kb_id: str | None = None
    session_id: str | None = None


__all__ = [
    "ChatOptions",
    "ChunkConfig",
    "RetrievalQuery",
]
