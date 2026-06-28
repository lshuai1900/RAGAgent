"""OpenAI-compatible Embedding 客户端实现。

使用 httpx async 调用 OpenAI 风格的 /embeddings 接口。
兼容 DashScope（qwen）/ OpenAI / DeepSeek 等供应商。

约束：
- API Key 从环境变量读取（api_key_ref 指定变量名），不得硬编码
- 批量请求支持（按 batch_size 分批调用）
- 可 Mock（httpx.AsyncClient 可注入）
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient

_logger = get_logger(__name__)


class OpenAICompatibleEmbeddingClient(BaseEmbeddingClient):
    """OpenAI 兼容 Embedding 客户端。

    通过 httpx async 调用 POST {base_url}/embeddings 接口。
    请求体：{"model": ..., "input": [...]}
    响应体：{"data": [{"embedding": [...]}, ...]}

    API Key 通过环境变量读取（变量名由 api_key_ref 指定），禁止硬编码。
    """

    def __init__(
        self,
        base_url: str,
        api_key_ref: str,
        model: str,
        dim: int,
        *,
        batch_size: int = 10,
        timeout: int = 60,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """初始化 Embedding 客户端。

        Args:
            base_url: API base URL（如 https://dashscope.aliyuncs.com/compatible-mode/v1）
            api_key_ref: API Key 的环境变量名（如 QWEN_API_KEY）
            model: Embedding 模型标识（如 text-embedding-v3）
            dim: 向量维度
            batch_size: 单次请求最大文本数（DashScope 单批上限 10，默认 10）
            timeout: HTTP 超时（秒）
            api_key: 显式传入 API Key（测试用，优先于环境变量）
            http_client: 可注入的 httpx.AsyncClient（测试用，便于 Mock）
        """
        self._base_url = base_url.rstrip("/")
        self._api_key_ref = api_key_ref
        self._model = model
        self._dim = dim
        self._batch_size = max(1, batch_size)
        self._timeout = timeout
        # 显式传入 > 环境变量；都无则为空字符串（调用时会抛 InfraException）
        self._api_key = api_key or os.environ.get(api_key_ref, "")
        # 外部可注入 http_client 便于 Mock；否则懒创建
        self._http_client = http_client
        self._owns_client = http_client is None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化。

        按 batch_size 分批调用，合并结果。

        Args:
            texts: 待向量化的文本列表

        Returns:
            向量列表，顺序与输入一致；空输入返回空列表

        Raises:
            InfraException: API Key 缺失 / HTTP 调用失败 / 响应解析失败
        """
        if not texts:
            return []

        self._ensure_api_key()

        client = self._get_client()
        url = f"{self._base_url}/embeddings"
        headers = self._build_headers()

        results: list[list[float]] = []
        # 分批调用，避免单请求体过大
        for batch_start in range(0, len(texts), self._batch_size):
            batch = texts[batch_start : batch_start + self._batch_size]
            # 仅发送 model / input / encoding_format，避免 DashScope 不兼容字段（dimensions/user 等）
            payload: dict[str, Any] = {
                "model": self._model,
                "input": batch,
                "encoding_format": "float",
            }

            _logger.debug(
                "embedding_request",
                model=self._model,
                batch_size=len(batch),
                batch_start=batch_start,
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
                # 异常信息必须包含响应体，便于定位 DashScope 4xx 原因（如 input 过长、字段不兼容）
                body_text = exc.response.text
                _logger.error(
                    "embedding_http_error",
                    status_code=exc.response.status_code,
                    body=body_text[:500],
                )
                raise InfraException(
                    message=(
                        f"Embedding API 调用失败 (HTTP {exc.response.status_code}): "
                        f"响应体={body_text[:1000]}"
                    ),
                    code=30010,
                    cause=exc,
                ) from exc
            except httpx.RequestError as exc:
                _logger.error("embedding_request_error", error=str(exc))
                raise InfraException(
                    message=f"Embedding API 请求失败: {exc}",
                    code=30011,
                    cause=exc,
                ) from exc

            try:
                body = response.json()
            except ValueError as exc:
                raise InfraException(
                    message="Embedding API 响应非 JSON",
                    code=30012,
                    cause=exc,
                ) from exc

            batch_vectors = self._parse_response(body)
            if len(batch_vectors) != len(batch):
                raise InfraException(
                    message=(f"Embedding 响应数量与请求不匹配: 请求 {len(batch)} 条，响应 {len(batch_vectors)} 条"),
                    code=30013,
                )
            results.extend(batch_vectors)

        _logger.info(
            "embedding_done",
            model=self._model,
            total_texts=len(texts),
            total_vectors=len(results),
        )
        return results

    async def embed_one(self, text: str) -> list[float]:
        """单条向量化（便捷方法）。"""
        vectors = await self.embed([text])
        if not vectors:
            raise InfraException(
                message="Embedding 单条向量化返回空结果",
                code=30014,
            )
        return vectors[0]

    def dim(self) -> int:
        """向量维度。"""
        return self._dim

    def model_name(self) -> str:
        """模型标识。"""
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
                message=(f"Embedding API Key 未配置：环境变量 {self._api_key_ref} 未设置"),
                code=30015,
            )

    def _build_headers(self) -> dict[str, str]:
        """构造请求头。"""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.AsyncClient:
        """获取 httpx.AsyncClient（懒创建）。"""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    @staticmethod
    def _parse_response(body: dict[str, Any]) -> list[list[float]]:
        """解析 OpenAI 风格的 embedding 响应。

        响应结构：{"data": [{"embedding": [...]}, ...], "model": ..., "usage": {...}}
        """
        data = body.get("data")
        if not isinstance(data, list):
            raise InfraException(
                message=f"Embedding 响应缺少 data 字段或格式错误: {body!r}",
                code=30016,
            )
        vectors: list[list[float]] = []
        for item in data:
            if not isinstance(item, dict):
                raise InfraException(
                    message="Embedding 响应 data 项非 dict",
                    code=30017,
                )
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise InfraException(
                    message="Embedding 响应缺少 embedding 字段或非 list",
                    code=30018,
                )
            vectors.append([float(x) for x in embedding])
        return vectors


__all__ = ["OpenAICompatibleEmbeddingClient"]
