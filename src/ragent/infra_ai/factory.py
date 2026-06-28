"""AI 客户端工厂：按配置构建 Embedding / LLM / Rerank 客户端。

MVP 第二批仅实现 Embedding 工厂方法。
LLM / Rerank 工厂方法在第三批补充。
"""

from __future__ import annotations

from ragent.framework.core.config import get_settings
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.embedding.openai_compat import OpenAICompatibleEmbeddingClient

_logger = get_logger(__name__)


def build_embedding_client(
    *,
    base_url: str | None = None,
    api_key_ref: str | None = None,
    model: str | None = None,
    dim: int | None = None,
    batch_size: int | None = None,
    timeout: int | None = None,
    api_key: str | None = None,
) -> BaseEmbeddingClient:
    """按配置构建 Embedding 客户端。

    优先使用显式参数，其次从全局 Settings 读取，最后用实现类默认值。

    Args:
        base_url: API base URL，None 时从 Settings 读取
        api_key_ref: API Key 环境变量名，None 时从 Settings 读取
        model: Embedding 模型标识，None 时从 Settings 读取
        dim: 向量维度，None 时从 Settings 读取
        batch_size: 单批最大文本数，None 时从 Settings 读取
        timeout: HTTP 超时（秒），None 时从 Settings 读取
        api_key: 显式 API Key（测试用，优先于环境变量）

    Returns:
        BaseEmbeddingClient 实现（OpenAICompatibleEmbeddingClient）
    """
    settings = get_settings()
    emb_cfg = settings.embedding

    client = OpenAICompatibleEmbeddingClient(
        base_url=base_url or emb_cfg.base_url,
        api_key_ref=api_key_ref or emb_cfg.api_key_ref,
        model=model or emb_cfg.model,
        dim=dim or emb_cfg.dim,
        batch_size=batch_size or emb_cfg.batch_size,
        timeout=timeout or emb_cfg.timeout,
        api_key=api_key,
    )
    _logger.info(
        "embedding_client_built",
        model=client.model_name(),
        dim=client.dim(),
        base_url=base_url or emb_cfg.base_url,
    )
    return client


__all__ = ["build_embedding_client"]
