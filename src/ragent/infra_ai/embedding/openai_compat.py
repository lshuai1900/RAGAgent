"""OpenAI-compatible Embedding client."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient

_logger = get_logger(__name__)


class OpenAICompatibleEmbeddingClient(BaseEmbeddingClient):
    """OpenAI-compatible Embedding client backed by async httpx."""

    def __init__(
        self,
        base_url: str,
        api_key_ref: str,
        model: str,
        dim: int,
        *,
        batch_size: int = 10,
        timeout: int = 60,
        send_dimensions: bool = False,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key_ref = api_key_ref
        self._model = model
        self._dim = dim
        self._batch_size = max(1, batch_size)
        self._timeout = timeout
        self._send_dimensions = send_dimensions
        self._api_key = api_key or os.environ.get(api_key_ref, "")
        self._http_client = http_client
        self._owns_client = http_client is None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches."""
        if not texts:
            return []

        self._ensure_api_key()

        client = self._get_client()
        url = f"{self._base_url}/embeddings"
        headers = self._build_headers()

        results: list[list[float]] = []
        batch_start = 0
        effective_batch_size = self._batch_size
        while batch_start < len(texts):
            batch = texts[batch_start : batch_start + effective_batch_size]
            payload: dict[str, Any] = {
                "model": self._model,
                "input": batch,
                "encoding_format": "float",
            }
            if self._send_dimensions:
                payload["dimensions"] = self._dim

            min_len, max_len = self._text_length_range(batch)
            self._log_request_context(
                "embedding_request",
                level="debug",
                input_count=len(texts),
                batch_size=len(batch),
                batch_start=batch_start,
                min_text_length=min_len,
                max_text_length=max_len,
            )

            try:
                response = await client.post(url, json=payload, headers=headers, timeout=self._timeout)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body_text = exc.response.text
                detail = self._extract_error_detail(body_text)
                max_batch_size = self._extract_max_batch_size(detail)
                if exc.response.status_code == 400 and max_batch_size is not None and 0 < max_batch_size < len(batch):
                    self._log_request_context(
                        "embedding_batch_size_retry",
                        level="warning",
                        input_count=len(texts),
                        batch_size=len(batch),
                        batch_start=batch_start,
                        min_text_length=min_len,
                        max_text_length=max_len,
                        status_code=exc.response.status_code,
                        error_body=body_text[:2000],
                        provider_max_batch_size=max_batch_size,
                        error_message=detail,
                    )
                    effective_batch_size = max_batch_size
                    continue
                self._log_request_context(
                    "embedding_http_error",
                    level="error",
                    input_count=len(texts),
                    batch_size=len(batch),
                    batch_start=batch_start,
                    min_text_length=min_len,
                    max_text_length=max_len,
                    status_code=exc.response.status_code,
                    error_body=body_text[:2000],
                    error_message=detail,
                )
                raise InfraException(
                    message=f"Embedding API 调用失败 (HTTP {exc.response.status_code}): {detail}",
                    code=30010,
                    cause=exc,
                ) from exc
            except httpx.RequestError as exc:
                self._log_request_context(
                    "embedding_request_error",
                    level="error",
                    input_count=len(texts),
                    batch_size=len(batch),
                    batch_start=batch_start,
                    min_text_length=min_len,
                    max_text_length=max_len,
                    error=str(exc),
                )
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
                    message=f"Embedding 响应数量与请求不匹配: 请求 {len(batch)} 条，响应 {len(batch_vectors)} 条",
                    code=30013,
                )
            results.extend(batch_vectors)
            batch_start += len(batch)

        _logger.info(
            "embedding_done",
            base_url=self._base_url,
            model=self._model,
            total_texts=len(texts),
            total_vectors=len(results),
            configured_batch_size=self._batch_size,
        )
        return results

    async def embed_one(self, text: str) -> list[float]:
        """Embed one text."""
        vectors = await self.embed([text])
        if not vectors:
            raise InfraException(
                message="Embedding 单条向量化返回空结果",
                code=30014,
            )
        return vectors[0]

    def dim(self) -> int:
        """Return embedding dimension."""
        return self._dim

    def model_name(self) -> str:
        """Return embedding model name."""
        return self._model

    async def close(self) -> None:
        """Close the owned HTTP client."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _ensure_api_key(self) -> None:
        if not self._api_key:
            raise InfraException(
                message=f"Embedding API Key 未配置：环境变量 {self._api_key_ref} 未设置",
                code=30015,
            )

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    def _log_request_context(self, event: str, *, level: str, **extra: Any) -> None:
        payload = {
            "base_url": self._base_url,
            "model": self._model,
            "configured_batch_size": self._batch_size,
            "send_dimensions": self._send_dimensions,
            "api_key_ref": self._api_key_ref,
            "api_key": self._mask_api_key(self._api_key),
            **extra,
        }
        if level == "error":
            _logger.error(event, **payload)
        elif level == "warning":
            _logger.warning(event, **payload)
        else:
            _logger.debug(event, **payload)

    @staticmethod
    def _parse_response(body: dict[str, Any]) -> list[list[float]]:
        """Parse an OpenAI-compatible embedding response."""
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

    @staticmethod
    def _mask_api_key(api_key: str) -> str:
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "***"
        return f"{api_key[:4]}...{api_key[-4:]}"

    @staticmethod
    def _text_length_range(texts: list[str]) -> tuple[int, int]:
        if not texts:
            return 0, 0
        lengths = [len(text) for text in texts]
        return min(lengths), max(lengths)

    @classmethod
    def _extract_error_detail(cls, body_text: str) -> str:
        if not body_text:
            return "响应体为空"
        try:
            body = json.loads(body_text)
        except json.JSONDecodeError:
            return body_text[:1000]

        detail = cls._find_first_string(body, ("message", "detail", "error_description", "code"))
        if detail:
            return detail[:1000]
        return body_text[:1000]

    @staticmethod
    def _extract_max_batch_size(detail: str) -> int | None:
        patterns = (
            r"(?:not be larger than|no larger than|larger than|at most|should not exceed)\s*(\d+)",
            r"(?:max(?:imum)?(?: batch size)?(?: is|:)?|batch size limit(?: is|:)?)\s*(\d+)",
        )
        lowered = detail.lower()
        if "batch" not in lowered:
            return None
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return int(match.group(1))
        return None

    @classmethod
    def _find_first_string(cls, value: Any, keys: tuple[str, ...]) -> str | None:
        if isinstance(value, dict):
            for key in keys:
                item = value.get(key)
                if isinstance(item, str) and item.strip():
                    return item
            for item in value.values():
                found = cls._find_first_string(item, keys)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = cls._find_first_string(item, keys)
                if found:
                    return found
        return None


__all__ = ["OpenAICompatibleEmbeddingClient"]
