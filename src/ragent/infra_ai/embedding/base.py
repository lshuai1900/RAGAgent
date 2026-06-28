"""Embedding 客户端抽象接口。

BaseEmbeddingClient 只依赖 domain，禁止依赖 persistence / rag / ingestion / api。
实现类（OpenAICompatibleEmbeddingClient）放在同包具体文件，
通过 infra_ai/factory.py 装配。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class BaseEmbeddingClient(Protocol):
    """Embedding 客户端抽象接口。

    实现类需提供：
    - embed(texts): 批量文本向量化
    - embed_one(text): 单条向量化（便捷方法）
    - dim(): 向量维度
    - model_name(): 模型标识
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化。

        Args:
            texts: 待向量化的文本列表

        Returns:
            向量列表，顺序与输入一致；空输入返回空列表
        """
        ...

    async def embed_one(self, text: str) -> list[float]:
        """单条向量化（便捷方法）。

        Args:
            text: 待向量化的文本

        Returns:
            单条文本对应的向量
        """
        ...

    def dim(self) -> int:
        """向量维度。"""
        ...

    def model_name(self) -> str:
        """模型标识。"""
        ...


__all__ = ["BaseEmbeddingClient"]
