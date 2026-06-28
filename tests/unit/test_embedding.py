"""T7 Embedding 客户端单元测试。

约束：
- 必须 Mock HTTP 请求，禁止真实调用外部模型
- 覆盖：正常批量、空输入、API Key 缺失、HTTP 错误、响应解析失败、批量分批
- 覆盖：embed_one / dim / model_name
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from ragent.framework.core.exceptions import InfraException
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.embedding.openai_compat import OpenAICompatibleEmbeddingClient


def _make_mock_response(
    status_code: int = 200,
    *,
    json_body: dict[str, Any] | None = None,
    text: str | None = None,
) -> httpx.Response:
    """构造 httpx.Response（不发起真实请求）。"""
    if json_body is not None:
        return httpx.Response(
            status_code=status_code,
            json=json_body,
            request=httpx.Request("POST", "https://example.com/embeddings"),
        )
    return httpx.Response(
        status_code=status_code,
        text=text or "",
        request=httpx.Request("POST", "https://example.com/embeddings"),
    )


def _make_mock_client(
    responses: list[httpx.Response],
) -> httpx.AsyncClient:
    """构造 Mock httpx.AsyncClient，按顺序返回指定响应。"""
    transport = httpx.MockTransport(lambda req: responses.pop(0))
    return httpx.AsyncClient(transport=transport)


def _make_capturing_client(
    responses: list[httpx.Response],
    captured: list[dict[str, Any]],
) -> httpx.AsyncClient:
    """构造 Mock httpx.AsyncClient，按顺序返回响应并捕获每次请求的 JSON body。"""
    import json

    def handler(req: httpx.Request) -> httpx.Response:
        try:
            captured.append(json.loads(req.content) if req.content else {})
        except (ValueError, json.JSONDecodeError):
            captured.append({})
        return responses.pop(0)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _make_embedding_response(vectors: list[list[float]], model: str = "text-embedding-v3") -> dict[str, Any]:
    """构造 OpenAI 风格的 embedding 响应 JSON。"""
    return {
        "object": "list",
        "data": [{"object": "embedding", "embedding": vec, "index": i} for i, vec in enumerate(vectors)],
        "model": model,
        "usage": {"prompt_tokens": 10, "total_tokens": 10},
    }


# ---------- 基本属性 ----------


def test_embedding_client_dim_and_model_name() -> None:
    """dim() 与 model_name() 返回构造参数。"""
    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="test-model",
        dim=768,
        api_key="dummy",
    )
    assert client.dim() == 768
    assert client.model_name() == "test-model"


def test_embedding_client_implements_base_protocol() -> None:
    """符合 BaseEmbeddingClient 协议。"""
    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=8,
        api_key="dummy",
    )
    assert isinstance(client, BaseEmbeddingClient)


# ---------- embed 正常路径 ----------


@pytest.mark.asyncio
async def test_embed_normal_batch() -> None:
    """正常批量向量化：返回向量列表，顺序与输入一致。"""
    vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    response_json = _make_embedding_response(vectors)
    mock_client = _make_mock_client([_make_mock_response(200, json_body=response_json)])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="test-model",
        dim=3,
        batch_size=10,
        api_key="dummy",
        http_client=mock_client,
    )

    result = await client.embed(["text1", "text2"])

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]
    await client.close()


@pytest.mark.asyncio
async def test_embed_empty_input_returns_empty() -> None:
    """空输入返回空列表，不调用 HTTP。"""
    mock_client = _make_mock_client([])  # 无响应

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=3,
        api_key="dummy",
        http_client=mock_client,
    )

    result = await client.embed([])
    assert result == []
    await client.close()


@pytest.mark.asyncio
async def test_embed_batch_split() -> None:
    """批量分批：batch_size=2 时，5 条输入触发 3 次请求。"""
    texts = ["t1", "t2", "t3", "t4", "t5"]
    # 3 批：[t1,t2], [t3,t4], [t5]
    responses = [
        _make_mock_response(200, json_body=_make_embedding_response([[0.1, 0.2], [0.3, 0.4]])),
        _make_mock_response(200, json_body=_make_embedding_response([[0.5, 0.6], [0.7, 0.8]])),
        _make_mock_response(200, json_body=_make_embedding_response([[0.9, 1.0]])),
    ]
    mock_client = _make_mock_client(responses)

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        batch_size=2,
        api_key="dummy",
        http_client=mock_client,
    )

    result = await client.embed(texts)

    assert len(result) == 5
    assert result[0] == [0.1, 0.2]
    assert result[-1] == [0.9, 1.0]
    await client.close()


# ---------- embed_one ----------


@pytest.mark.asyncio
async def test_embed_one_returns_single_vector() -> None:
    """embed_one 返回单条向量。"""
    response_json = _make_embedding_response([[0.5, 0.5, 0.5]])
    mock_client = _make_mock_client([_make_mock_response(200, json_body=response_json)])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=3,
        api_key="dummy",
        http_client=mock_client,
    )

    vec = await client.embed_one("hello")
    assert vec == [0.5, 0.5, 0.5]
    await client.close()


# ---------- 错误路径 ----------


@pytest.mark.asyncio
async def test_embed_missing_api_key_raises_infra_exception() -> None:
    """API Key 缺失：抛 InfraException。"""
    import os

    # 确保环境变量未设置
    os.environ.pop("MISSING_KEY_FOR_TEST", None)
    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="MISSING_KEY_FOR_TEST",
        model="m",
        dim=3,
        api_key=None,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["text"])
    assert exc_info.value.code == 30015


@pytest.mark.asyncio
async def test_embed_http_error_raises_infra_exception() -> None:
    """HTTP 4xx/5xx：抛 InfraException。"""
    error_response = _make_mock_response(401, text='{"error": "invalid api key"}')
    mock_client = _make_mock_client([error_response])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=3,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["text"])
    assert exc_info.value.code == 30010
    await client.close()


@pytest.mark.asyncio
async def test_embed_response_count_mismatch_raises() -> None:
    """响应向量数与请求数不匹配：抛 InfraException。"""
    # 请求 2 条，响应只返回 1 条
    bad_response = _make_embedding_response([[0.1, 0.2]])
    mock_client = _make_mock_client([_make_mock_response(200, json_body=bad_response)])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["t1", "t2"])
    assert exc_info.value.code == 30013
    await client.close()


@pytest.mark.asyncio
async def test_embed_invalid_json_response_raises() -> None:
    """响应非 JSON：抛 InfraException。"""
    bad_response = _make_mock_response(200, text="not json at all")
    mock_client = _make_mock_client([bad_response])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["t1"])
    assert exc_info.value.code in (30012, 30016, 30017, 30018)
    await client.close()


@pytest.mark.asyncio
async def test_embed_missing_data_field_raises() -> None:
    """响应缺少 data 字段：抛 InfraException。"""
    bad_response = _make_mock_response(200, json_body={"model": "m"})
    mock_client = _make_mock_client([bad_response])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["t1"])
    assert exc_info.value.code == 30016
    await client.close()


# ---------- API Key 来源 ----------


@pytest.mark.asyncio
async def test_api_key_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """API Key 从环境变量读取（api_key_ref 指定变量名）。"""
    monkeypatch.setenv("MY_EMBEDDING_KEY", "env-key-value")

    response_json = _make_embedding_response([[0.1, 0.2]])
    mock_client = _make_mock_client([_make_mock_response(200, json_body=response_json)])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="MY_EMBEDDING_KEY",
        model="m",
        dim=2,
        http_client=mock_client,
    )

    # 调用成功即说明 API Key 已读取
    result = await client.embed(["t1"])
    assert result == [[0.1, 0.2]]
    await client.close()


# ---------- 请求体契约 ----------


@pytest.mark.asyncio
async def test_default_payload_contains_required_fields() -> None:
    """默认请求体包含 model / input / encoding_format。"""
    captured: list[dict[str, Any]] = []
    response_json = _make_embedding_response([[0.1, 0.2]])
    mock_client = _make_capturing_client([_make_mock_response(200, json_body=response_json)], captured)

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="text-embedding-v3",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    await client.embed(["hello"])

    assert len(captured) == 1
    payload = captured[0]
    assert payload["model"] == "text-embedding-v3"
    assert payload["input"] == ["hello"]
    assert payload["encoding_format"] == "float"
    await client.close()


@pytest.mark.asyncio
async def test_default_payload_does_not_contain_dashscope_incompatible_fields() -> None:
    """默认请求体不包含 DashScope 不兼容字段（dimensions / user）。"""
    captured: list[dict[str, Any]] = []
    response_json = _make_embedding_response([[0.1, 0.2]])
    mock_client = _make_capturing_client([_make_mock_response(200, json_body=response_json)], captured)

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="text-embedding-v3",
        dim=1024,
        api_key="dummy",
        http_client=mock_client,
    )

    await client.embed(["hello"])

    payload = captured[0]
    assert "dimensions" not in payload
    assert "user" not in payload
    await client.close()


@pytest.mark.asyncio
async def test_payload_sends_dimensions_only_when_enabled() -> None:
    """send_dimensions=True 时才发送 dimensions 字段。"""
    captured: list[dict[str, Any]] = []
    response_json = _make_embedding_response([[0.1, 0.2, 0.3]])
    mock_client = _make_capturing_client([_make_mock_response(200, json_body=response_json)], captured)

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="custom-embedding",
        dim=3,
        send_dimensions=True,
        api_key="dummy",
        http_client=mock_client,
    )

    await client.embed(["hello"])

    payload = captured[0]
    assert payload["dimensions"] == 3
    await client.close()


@pytest.mark.asyncio
async def test_embed_splits_at_sixteen_texts_by_default() -> None:
    """默认 batch_size=16：17 条 input 触发 2 次请求（16 + 1），结果按原顺序合并。"""
    texts = [f"t{i}" for i in range(17)]
    # 第 1 批返回 16 条向量，第 2 批返回 1 条向量
    responses = [
        _make_mock_response(
            200,
            json_body=_make_embedding_response([[float(i), 0.0] for i in range(16)]),
        ),
        _make_mock_response(
            200,
            json_body=_make_embedding_response([[100.0, 0.0]]),
        ),
    ]
    captured: list[dict[str, Any]] = []
    mock_client = _make_capturing_client(responses, captured)

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
        # 不传 batch_size，使用默认值 16
    )

    result = await client.embed(texts)

    assert len(result) == 17
    # 2 次请求
    assert len(captured) == 2
    # 第 1 批 16 条，第 2 批 1 条
    assert len(captured[0]["input"]) == 16
    assert len(captured[1]["input"]) == 1
    # 顺序合并：前 16 条来自第 1 批，最后 1 条来自第 2 批
    assert result[0] == [0.0, 0.0]
    assert result[15] == [15.0, 0.0]
    assert result[16] == [100.0, 0.0]
    await client.close()


@pytest.mark.asyncio
async def test_http_400_error_message_contains_response_body() -> None:
    """HTTP 400 时异常信息包含 response body，便于定位 DashScope 报错原因。"""
    error_body = '{"error":{"message":"input data length exceeds max limit","code":"BadRequest"}}'
    error_response = _make_mock_response(400, text=error_body)
    mock_client = _make_mock_client([error_response])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["text"])
    assert exc_info.value.code == 30010
    assert "400" in exc_info.value.message
    assert "input data length exceeds max limit" in exc_info.value.message
    await client.close()


@pytest.mark.asyncio
async def test_http_400_error_message_extracts_nested_error_message() -> None:
    """HTTP 400 时优先提取 error.message，避免前端只看到原始 HTTP 状态。"""
    error_body = {
        "error": {
            "message": "This model does not support dimensions",
            "type": "invalid_request_error",
        }
    }
    error_response = _make_mock_response(400, json_body=error_body)
    mock_client = _make_mock_client([error_response])

    client = OpenAICompatibleEmbeddingClient(
        base_url="https://example.com/v1",
        api_key_ref="TEST_API_KEY",
        model="m",
        dim=2,
        api_key="dummy",
        http_client=mock_client,
    )

    with pytest.raises(InfraException) as exc_info:
        await client.embed(["text"])
    assert exc_info.value.code == 30010
    assert exc_info.value.message == "Embedding API 调用失败 (HTTP 400): This model does not support dimensions"
    await client.close()
