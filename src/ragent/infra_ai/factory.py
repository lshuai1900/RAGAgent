"""AI 客户端工厂：按配置构建 Embedding / LLM / Rerank 客户端。

第三批补充 LLM 工厂方法。Rerank 工厂方法 MVP 仅返回 IdentityReranker。
"""

from __future__ import annotations

from ragent.framework.core.config import get_settings
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.embedding.openai_compat import OpenAICompatibleEmbeddingClient
from ragent.infra_ai.llm.base import BaseLLMClient
from ragent.infra_ai.llm.openai_compat import OpenAICompatibleLLMClient
from ragent.infra_ai.rerank.base import BaseReranker
from ragent.infra_ai.rerank.identity import IdentityReranker

_logger = get_logger(__name__)


def build_embedding_client(
    *,
    base_url: str | None = None,
    api_key_ref: str | None = None,
    model: str | None = None,
    dim: int | None = None,
    batch_size: int | None = None,
    timeout: int | None = None,
    send_dimensions: bool | None = None,
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
        send_dimensions=emb_cfg.send_dimensions if send_dimensions is None else send_dimensions,
        api_key=api_key,
    )
    _logger.info(
        "embedding_client_built",
        model=client.model_name(),
        dim=client.dim(),
        base_url=base_url or emb_cfg.base_url,
        batch_size=batch_size or emb_cfg.batch_size,
        send_dimensions=emb_cfg.send_dimensions if send_dimensions is None else send_dimensions,
    )
    return client


def build_llm_client(
    *,
    base_url: str | None = None,
    api_key_ref: str | None = None,
    model: str | None = None,
    timeout: int | None = None,
    api_key: str | None = None,
) -> BaseLLMClient:
    """按配置构建 LLM 客户端。

    优先使用显式参数，其次从全局 Settings 读取，最后用实现类默认值。

    Args:
        base_url: API base URL，None 时从 Settings 读取
        api_key_ref: API Key 环境变量名，None 时从 Settings 读取
        model: LLM 模型标识，None 时从 Settings 读取
        timeout: HTTP 超时（秒），None 时从 Settings 读取
        api_key: 显式 API Key（测试用，优先于环境变量）

    Returns:
        BaseLLMClient 实现（OpenAICompatibleLLMClient）
    """
    settings = get_settings()
    llm_cfg = settings.llm

    client = OpenAICompatibleLLMClient(
        base_url=base_url or llm_cfg.base_url,
        api_key_ref=api_key_ref or llm_cfg.api_key_ref,
        model=model or llm_cfg.model,
        timeout=timeout or llm_cfg.timeout,
        api_key=api_key,
    )
    _logger.info(
        "llm_client_built",
        model=client.model_name(),
        base_url=base_url or llm_cfg.base_url,
    )
    return client


def build_reranker() -> BaseReranker:
    """构建 Rerank 客户端（MVP 仅 IdentityReranker）。

    Returns:
        IdentityReranker 实例（直通不排序）
    """
    _logger.info("reranker_built", impl="identity")
    return IdentityReranker()


__all__ = ["build_embedding_client", "build_llm_client", "build_reranker"]
