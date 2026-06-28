"""OpenAI-compatible LLM 客户端实现。

使用 httpx async 调用 OpenAI 风格的 /chat/completions 接口。
兼容 DashScope（qwen）/ OpenAI / DeepSeek 等供应商。

约束：
- API Key 从环境变量读取（api_key_ref 指定变量名），不得硬编码
- 支持非流式 chat 与流式 stream_chat（解析 SSE delta）
- 流式返回 AsyncIterator[ChatChunk]，首包可用于 SSE start 事件探测
- 可 Mock（httpx.AsyncClient 可注入 + stream_chat 可被 Mock 替换）
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ragent.domain.dto import ChatChunk, ChatMessage
from ragent.domain.value_objects import ChatOptions
from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.llm.base import BaseLLMClient

_logger = get_logger(__name__)


class OpenAICompatibleLLMClient(BaseLLMClient):
    """OpenAI 兼容 LLM 客户端。

    - chat: POST {base_url}/chat/completions（stream=false），返回完整文本
    - stream_chat: POST {base_url}/chat/completions（stream=true），
      解析 SSE 事件流，逐个 yield ChatChunk

    API Key 通过环境变量读取（变量名由 api_key_ref 指定），禁止硬编码。
    """

    def __init__(
        self,
        base_url: str,
        api_key_ref: str,
        model: str,
        *,
        timeout: int = 60,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """初始化 LLM 客户端。

        Args:
            base_url: API base URL（如 https://dashscope.aliyuncs.com/compatible-mode/v1）
            api_key_ref: API Key 的环境变量名（如 QWEN_API_KEY）
            model: 默认对话模型（如 qwen-plus）
            timeout: HTTP 超时（秒）
            api_key: 显式传入 API Key（测试用，优先于环境变量）
            http_client: 可注入的 httpx.AsyncClient（测试用，便于 Mock）
        """
        self._base_url = base_url.rstrip("/")
        self._api_key_ref = api_key_ref
        self._model = model
        self._timeout = timeout
        # 显式传入 > 环境变量；都无则为空字符串（调用时会抛 InfraException）
        self._api_key = api_key or os.environ.get(api_key_ref, "")
        # 外部可注入 http_client 便于 Mock；否则懒创建
        self._http_client = http_client
        self._owns_client = http_client is None

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> str:
        """非流式对话。

        Args:
            messages: 消息列表
            options: 对话选项

        Returns:
            完整回复文本

        Raises:
            InfraException: API Key 缺失 / HTTP 调用失败 / 响应解析失败
        """
        self._ensure_api_key()

        client = self._get_client()
        url = f"{self._base_url}/chat/completions"
        headers = self._build_headers()
        payload = self._build_payload(messages, options, stream=False)

        _logger.debug(
            "llm_chat_request",
            model=self._model,
            message_count=len(messages),
            temperature=options.temperature,
        )

        try:
            response = await client.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            _logger.error(
                "llm_chat_http_error",
                status_code=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise InfraException(
                message=f"LLM chat 调用失败 (HTTP {exc.response.status_code})",
                code=30030,
                cause=exc,
            ) from exc
        except httpx.RequestError as exc:
            _logger.error("llm_chat_request_error", error=str(exc))
            raise InfraException(
                message=f"LLM chat 请求失败: {exc}",
                code=30031,
                cause=exc,
            ) from exc

        try:
            body = response.json()
        except ValueError as exc:
            raise InfraException(
                message="LLM chat 响应非 JSON",
                code=30032,
                cause=exc,
            ) from exc

        return self._parse_chat_response(body)

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[ChatChunk]:
        """流式对话，解析 SSE delta。

        使用 httpx 的 stream() 按行读取 SSE 事件：
        - 每个事件以 "data: " 前缀
        - "data: [DONE]" 表示流结束
        - 其余为 JSON：{"choices": [{"delta": {"content": "..."}, "finish_reason": null|...}]}

        首包（第一个非空 delta）到达时记录日志，便于 SSE start 事件探测。

        Args:
            messages: 消息列表
            options: 对话选项

        Yields:
            ChatChunk（含 delta 增量与 finish_reason）

        Raises:
            InfraException: API Key 缺失 / HTTP 调用失败 / 响应解析失败
        """
        self._ensure_api_key()

        client = self._get_client()
        url = f"{self._base_url}/chat/completions"
        headers = self._build_headers()
        payload = self._build_payload(messages, options, stream=True)

        _logger.info(
            "llm_stream_chat_request",
            model=self._model,
            message_count=len(messages),
        )

        first_chunk_seen = False
        try:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        # 忽略非 data 行（如 event: / 注释）
                        continue
                    data_str = line[len("data:") :].strip()
                    if data_str == "[DONE]":
                        # 流结束
                        return
                    try:
                        chunk_data = json.loads(data_str)
                    except ValueError as exc:
                        _logger.warning(
                            "llm_stream_parse_error",
                            line=data_str[:200],
                            error=str(exc),
                        )
                        continue

                    chunk = self._parse_stream_chunk(chunk_data)
                    if chunk is None:
                        continue

                    if not first_chunk_seen:
                        first_chunk_seen = True
                        _logger.info("llm_stream_first_chunk_seen", model=self._model)

                    yield chunk
        except httpx.HTTPStatusError as exc:
            _logger.error(
                "llm_stream_http_error",
                status_code=exc.response.status_code,
                body=exc.response.text[:500],
            )
            raise InfraException(
                message=f"LLM stream_chat 调用失败 (HTTP {exc.response.status_code})",
                code=30033,
                cause=exc,
            ) from exc
        except httpx.RequestError as exc:
            _logger.error("llm_stream_request_error", error=str(exc))
            raise InfraException(
                message=f"LLM stream_chat 请求失败: {exc}",
                code=30034,
                cause=exc,
            ) from exc

    def model_name(self) -> str:
        """返回模型标识。"""
        return self._model

    async def close(self) -> None:
        """关闭自建的 httpx.AsyncClient（外部注入的不关闭）。"""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _ensure_api_key(self) -> None:
        """确保 API Key 可用，否则抛 InfraException。"""
        if not self._api_key:
            raise InfraException(
                message=(
                    f"LLM API Key 未配置：环境变量 {self._api_key_ref} 未设置"
                ),
                code=30035,
            )

    def _build_headers(self) -> dict[str, str]:
        """构造请求头。"""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
        *,
        stream: bool,
    ) -> dict[str, Any]:
        """构造 OpenAI 风格的请求体。

        Args:
            messages: 消息列表
            options: 对话选项
            stream: 是否流式

        Returns:
            请求体 dict
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": options.temperature,
            "top_p": options.top_p,
            "stream": stream,
        }
        if options.max_tokens is not None:
            payload["max_tokens"] = options.max_tokens
        if options.stop:
            payload["stop"] = options.stop
        return payload

    def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx.AsyncClient（懒创建）。"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    @staticmethod
    def _parse_chat_response(body: dict[str, Any]) -> str:
        """解析非流式响应。

        响应结构：{"choices": [{"message": {"role": "assistant", "content": "..."}}], ...}
        """
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise InfraException(
                message=f"LLM chat 响应缺少 choices 字段或为空: {body!r}",
                code=30036,
            )
        first = choices[0]
        if not isinstance(first, dict):
            raise InfraException(
                message="LLM chat 响应 choices[0] 非 dict",
                code=30037,
            )
        message = first.get("message")
        if not isinstance(message, dict):
            raise InfraException(
                message="LLM chat 响应缺少 message 字段",
                code=30038,
            )
        content = message.get("content")
        if not isinstance(content, str):
            raise InfraException(
                message="LLM chat 响应缺少 content 字段或非 str",
                code=30039,
            )
        return content

    @staticmethod
    def _parse_stream_chunk(chunk_data: dict[str, Any]) -> ChatChunk | None:
        """解析单个 SSE data chunk。

        结构：{"choices": [{"delta": {"content": "..."}, "finish_reason": null|...}]}

        Args:
            chunk_data: 单个 SSE 事件的 JSON dict

        Returns:
            ChatChunk 或 None（无 delta 内容时跳过）
        """
        choices = chunk_data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first = choices[0]
        if not isinstance(first, dict):
            return None
        delta = first.get("delta")
        finish_reason = first.get("finish_reason")
        content = ""
        if isinstance(delta, dict):
            c = delta.get("content")
            if isinstance(c, str):
                content = c
        # 完全空（无 content 且无 finish_reason）跳过
        if not content and finish_reason is None:
            return None
        return ChatChunk(delta=content, finish_reason=finish_reason)


__all__ = ["OpenAICompatibleLLMClient"]
