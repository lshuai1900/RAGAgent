"""T11 LLM 客户端单元测试。

约束：
- 必须 Mock HTTP 请求，禁止真实调用外部模型
- 覆盖：
  - chat 非流式正常响应
  - stream_chat 流式响应（解析 SSE delta）
  - stream_chat [DONE] 终止符
  - API Key 缺失抛 InfraException
  - HTTP 错误抛 InfraException
  - 响应解析失败抛 InfraException
  - API Key 从环境变量读取
  - model_name 返回构造参数
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ragent.domain.dto import ChatChunk, ChatMessage
from ragent.domain.value_objects import ChatOptions
from ragent.framework.core.exceptions import InfraException
from ragent.infra_ai.llm.base import BaseLLMClient
from ragent.infra_ai.llm.openai_compat import OpenAICompatibleLLMClient

# ---------- 工具函数 ----------


def _make_chat_response(content: str, model: str = "qwen-plus") -> dict[str, Any]:
    """构造 OpenAI 风格的非流式 chat 响应。"""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _make_stream_lines(
    deltas: list[tuple[str, str | None]],
) -> bytes:
    """构造 OpenAI 风格的 SSE 流响应（按行返回 bytes）。

    Args:
        deltas: [(content, finish_reason)] 列表；finish_reason 非 None 时表示结束 chunk

    Returns:
        SSE 文本（每行 data: {...}\\n\\n），以 data: [DONE] 结尾
    """
    lines: list[str] = []
    for content, finish_reason in deltas:
        chunk: dict[str, Any] = {
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "model": "qwen-plus",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content} if content else {},
                    "finish_reason": finish_reason,
                }
            ],
        }
        lines.append(f"data: {json.dumps(chunk, ensure_ascii=False)}")
    lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode("utf-8")


def _make_mock_transport(
    *,
    json_body: dict[str, Any] | None = None,
    stream_bytes: bytes | None = None,
    status_code: int = 200,
    text: str | None = None,
) -> httpx.MockTransport:
    """构造 Mock transport，按需返回非流式 / 流式 / 错误响应。"""
    if stream_bytes is not None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=status_code,
                content=stream_bytes,
                headers={"content-type": "text/event-stream"},
                request=request,
            )
    elif json_body is not None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=status_code,
                json=json_body,
                request=request,
            )
    else:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=status_code,
                text=text or "",
                request=request,
            )
    return httpx.MockTransport(handler)


def _make_client(transport: httpx.MockTransport) -> OpenAICompatibleLLMClient:
    """构造注入 Mock transport 的 LLM 客户端。"""
    http_client = httpx.AsyncClient(transport=transport)
    return OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_LLM_KEY",
        model="qwen-plus",
        timeout=10,
        api_key="dummy-key",
        http_client=http_client,
    )


# ---------- 基本属性 ----------


def test_llm_client_model_name() -> None:
    """model_name() 返回构造参数。"""
    client = OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_LLM_KEY",
        model="my-model",
        api_key="dummy",
    )
    assert client.model_name() == "my-model"


def test_llm_client_implements_base_protocol() -> None:
    """符合 BaseLLMClient 协议。"""
    client = OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_LLM_KEY",
        model="m",
        api_key="dummy",
    )
    assert isinstance(client, BaseLLMClient)


# ---------- chat 非流式 ----------


@pytest.mark.asyncio
async def test_chat_normal_response() -> None:
    """chat 正常返回完整文本。"""
    transport = _make_mock_transport(json_body=_make_chat_response("你好，世界"))
    client = _make_client(transport)

    result = await client.chat(
        [ChatMessage(role="user", content="hi")],
        ChatOptions(),
    )
    assert result == "你好，世界"
    await client.close()


@pytest.mark.asyncio
async def test_chat_with_options_in_payload() -> None:
    """ChatOptions 中的 temperature/top_p/max_tokens 被传入请求体。"""
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=200,
            json=_make_chat_response("ok"),
            request=request,
        )

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    options = ChatOptions(temperature=0.5, top_p=0.8, max_tokens=100, stop=["END"])
    await client.chat([ChatMessage(role="user", content="q")], options)

    body = captured["body"]
    assert body["temperature"] == 0.5
    assert body["top_p"] == 0.8
    assert body["max_tokens"] == 100
    assert body["stop"] == ["END"]
    assert body["model"] == "qwen-plus"
    assert body["messages"] == [{"role": "user", "content": "q"}]
    await client.close()


@pytest.mark.asyncio
async def test_chat_missing_api_key_raises() -> None:
    """API Key 缺失：抛 InfraException。"""
    import os

    os.environ.pop("MISSING_LLM_KEY", None)
    client = OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="MISSING_LLM_KEY",
        model="m",
        api_key=None,
    )
    with pytest.raises(InfraException) as exc_info:
        await client.chat([ChatMessage(role="user", content="x")], ChatOptions())
    assert exc_info.value.code == 30035


@pytest.mark.asyncio
async def test_chat_http_error_raises() -> None:
    """HTTP 4xx/5xx：抛 InfraException。"""
    transport = _make_mock_transport(status_code=401, text='{"error":"bad key"}')
    client = _make_client(transport)

    with pytest.raises(InfraException) as exc_info:
        await client.chat([ChatMessage(role="user", content="x")], ChatOptions())
    assert exc_info.value.code == 30030
    await client.close()


@pytest.mark.asyncio
async def test_chat_invalid_json_raises() -> None:
    """响应非 JSON：抛 InfraException。"""
    transport = _make_mock_transport(text="not json")
    client = _make_client(transport)

    with pytest.raises(InfraException) as exc_info:
        await client.chat([ChatMessage(role="user", content="x")], ChatOptions())
    assert exc_info.value.code in (30032, 30036, 30037, 30038, 30039)
    await client.close()


@pytest.mark.asyncio
async def test_chat_missing_choices_raises() -> None:
    """响应缺少 choices：抛 InfraException。"""
    transport = _make_mock_transport(json_body={"model": "m"})
    client = _make_client(transport)

    with pytest.raises(InfraException) as exc_info:
        await client.chat([ChatMessage(role="user", content="x")], ChatOptions())
    assert exc_info.value.code == 30036
    await client.close()


# ---------- stream_chat 流式 ----------


@pytest.mark.asyncio
async def test_stream_chat_normal() -> None:
    """stream_chat 正常流式：逐个 yield ChatChunk。"""
    stream_bytes = _make_stream_lines(
        [
            ("你好", None),
            ("，", None),
            ("世界", None),
            ("", "stop"),
        ]
    )
    transport = _make_mock_transport(stream_bytes=stream_bytes)
    client = _make_client(transport)

    chunks: list[ChatChunk] = []
    async for chunk in client.stream_chat(
        [ChatMessage(role="user", content="hi")],
        ChatOptions(),
    ):
        chunks.append(chunk)

    # 至少 3 个 delta + 1 个 finish_reason
    assert len(chunks) >= 3
    deltas = [c.delta for c in chunks if c.delta]
    assert "你好" in deltas
    assert "世界" in deltas
    # 最后一个 chunk 含 finish_reason
    finish_chunks = [c for c in chunks if c.finish_reason is not None]
    assert len(finish_chunks) == 1
    assert finish_chunks[0].finish_reason == "stop"
    await client.close()


@pytest.mark.asyncio
async def test_stream_chat_aggregates_to_full_text() -> None:
    """流式 chunk 拼接后等于完整文本。"""
    stream_bytes = _make_stream_lines(
        [
            ("RAG", None),
            (" 是", None),
            (" 检索增强生成", None),
            ("", "stop"),
        ]
    )
    transport = _make_mock_transport(stream_bytes=stream_bytes)
    client = _make_client(transport)

    parts: list[str] = []
    async for chunk in client.stream_chat(
        [ChatMessage(role="user", content="q")],
        ChatOptions(),
    ):
        if chunk.delta:
            parts.append(chunk.delta)

    assert "".join(parts) == "RAG 是 检索增强生成"
    await client.close()


@pytest.mark.asyncio
async def test_stream_chat_ignores_non_data_lines() -> None:
    """非 data: 前缀的行（如 event: 注释）被忽略。"""
    # 手工构造含 event: 行与注释行
    lines = [
        ": heartbeat",
        'event: ping',
        'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}',
        'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        'data: [DONE]',
    ]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    transport = _make_mock_transport(stream_bytes=raw)
    client = _make_client(transport)

    chunks: list[ChatChunk] = []
    async for chunk in client.stream_chat(
        [ChatMessage(role="user", content="x")],
        ChatOptions(),
    ):
        chunks.append(chunk)

    deltas = [c.delta for c in chunks if c.delta]
    assert deltas == ["hi"]
    await client.close()


@pytest.mark.asyncio
async def test_stream_chat_http_error_raises() -> None:
    """stream_chat HTTP 错误：抛 InfraException。"""
    transport = _make_mock_transport(
        stream_bytes=b'data: {"error":"unauthorized"}\n\n',
        status_code=401,
    )
    client = _make_client(transport)

    with pytest.raises(InfraException) as exc_info:
        async for _ in client.stream_chat(
            [ChatMessage(role="user", content="x")],
            ChatOptions(),
        ):
            pass
    assert exc_info.value.code == 30033
    await client.close()


@pytest.mark.asyncio
async def test_stream_chat_missing_api_key_raises() -> None:
    """stream_chat API Key 缺失：抛 InfraException。"""
    import os

    os.environ.pop("MISSING_LLM_KEY_STREAM", None)
    client = OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="MISSING_LLM_KEY_STREAM",
        model="m",
        api_key=None,
    )
    with pytest.raises(InfraException) as exc_info:
        async for _ in client.stream_chat(
            [ChatMessage(role="user", content="x")],
            ChatOptions(),
        ):
            pass
    assert exc_info.value.code == 30035


# ---------- API Key 来源 ----------


@pytest.mark.asyncio
async def test_api_key_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """API Key 从环境变量读取（api_key_ref 指定变量名）。"""
    monkeypatch.setenv("MY_LLM_KEY", "env-llm-key-value")
    transport = _make_mock_transport(json_body=_make_chat_response("ok"))

    http_client = httpx.AsyncClient(transport=transport)
    client = OpenAICompatibleLLMClient(
        base_url="https://example.com/v1",
        api_key_ref="MY_LLM_KEY",
        model="m",
        http_client=http_client,
    )

    result = await client.chat([ChatMessage(role="user", content="q")], ChatOptions())
    assert result == "ok"
    await client.close()


# ---------- 内部解析方法 ----------


def test_parse_stream_chunk_with_content() -> None:
    """_parse_stream_chunk 含 content 的 chunk 正常解析。"""
    chunk = OpenAICompatibleLLMClient._parse_stream_chunk(
        {"choices": [{"delta": {"content": "abc"}, "finish_reason": None}]}
    )
    assert chunk is not None
    assert chunk.delta == "abc"
    assert chunk.finish_reason is None


def test_parse_stream_chunk_with_finish_reason() -> None:
    """_parse_stream_chunk 含 finish_reason 的 chunk 正常解析。"""
    chunk = OpenAICompatibleLLMClient._parse_stream_chunk(
        {"choices": [{"delta": {}, "finish_reason": "stop"}]}
    )
    assert chunk is not None
    assert chunk.delta == ""
    assert chunk.finish_reason == "stop"


def test_parse_stream_chunk_empty_returns_none() -> None:
    """_parse_stream_chunk 无 content 且无 finish_reason 返回 None。"""
    chunk = OpenAICompatibleLLMClient._parse_stream_chunk(
        {"choices": [{"delta": {}, "finish_reason": None}]}
    )
    assert chunk is None


def test_parse_stream_chunk_missing_choices_returns_none() -> None:
    """_parse_stream_chunk 缺少 choices 返回 None。"""
    chunk = OpenAICompatibleLLMClient._parse_stream_chunk({"model": "m"})
    assert chunk is None
