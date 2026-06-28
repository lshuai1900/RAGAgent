"""LLM 客户端抽象接口。

BaseLLMClient 只依赖 domain.dto.ChatChunk / ChatMessage 与 domain.value_objects.ChatOptions，
禁止依赖 persistence / rag / api。
实现类（OpenAICompatibleLLMClient）放在同包具体文件，通过 infra_ai/factory.py 装配。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ragent.domain.dto import ChatChunk, ChatMessage
from ragent.domain.value_objects import ChatOptions


@runtime_checkable
class BaseLLMClient(Protocol):
    """LLM 客户端抽象接口。

    实现类需提供：
    - chat: 非流式对话，返回完整文本
    - stream_chat: 流式对话，返回 AsyncIterator[ChatChunk]
    - model_name: 模型标识

    约束：
    - stream_chat 必须返回 AsyncIterator[ChatChunk]，首包可用于 SSE start 事件探测
    - API Key 从配置或环境变量读取，不得硬编码
    - LLM 调用必须可 Mock（便于 CI）
    """

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> str:
        """非流式对话。

        Args:
            messages: 消息列表（role/content）
            options: 对话选项（temperature/top_p/max_tokens/stop）

        Returns:
            完整回复文本
        """
        ...

    def stream_chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[ChatChunk]:
        """流式对话。

        Args:
            messages: 消息列表
            options: 对话选项

        Returns:
            ChatChunk 异步迭代器，每个 chunk 含 delta（增量）与 finish_reason（结束原因）
        """
        ...

    def model_name(self) -> str:
        """模型标识。"""
        ...


__all__ = ["BaseLLMClient"]
