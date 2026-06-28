"""知识库 API Schema（Pydantic v2）。

顶层独立，可依赖 domain（用枚举/DTO），不得被 domain 依赖。
严格与 SQLAlchemy ORM Model 分离。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from ragent.domain.enums import KnowledgeBaseStatus


class KnowledgeBaseCreate(BaseModel):
    """创建知识库请求。"""

    name: str = Field(..., min_length=1, max_length=128, description="知识库名称（唯一）")
    description: str | None = Field(None, max_length=512, description="描述")
    embedding_model: str = Field("text-embedding-v3", max_length=64, description="Embedding 模型标识")
    embedding_dim: int = Field(1024, gt=0, le=8192, description="向量维度")
    chunk_strategy: str = Field("recursive", max_length=32, description="分块策略")
    chunk_size: int = Field(512, gt=0, le=8192, description="分块大小（字符数）")
    chunk_overlap: int = Field(64, ge=0, lt=8192, description="分块重叠（字符数）")

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info: ValidationInfo) -> int:
        """overlap 必须小于 chunk_size。"""
        chunk_size = info.data.get("chunk_size")
        if chunk_size is not None and v >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size")
        return v

    @field_validator("chunk_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """分块策略必须是 fixed / sentence / recursive 之一。"""
        allowed = {"fixed", "sentence", "recursive"}
        if v not in allowed:
            raise ValueError(f"chunk_strategy 必须是 {allowed} 之一")
        return v


class KnowledgeBaseUpdate(BaseModel):
    """更新知识库请求（支持修改名称、描述、状态）。

    所有字段可选，仅传入的字段会被更新（部分更新语义）。
    名称变更时会做唯一性校验。
    """

    name: str | None = Field(None, min_length=1, max_length=128, description="知识库名称（唯一）")
    description: str | None = Field(None, max_length=512, description="描述")
    status: KnowledgeBaseStatus | None = Field(None, description="状态")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """名称非空校验：去除首尾空白后不能为空。"""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("知识库名称不能为空")
        return stripped


class KnowledgeBaseOut(BaseModel):
    """知识库响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    collection_name: str
    embedding_dim: int
    embedding_model: str
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    document_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseDeleteResponse(BaseModel):
    """知识库删除响应。"""

    id: str
    status: str
    collection_name: str


class KnowledgeBasePage(BaseModel):
    """知识库分页响应。"""

    items: list[KnowledgeBaseOut]
    total: int
    page: int
    page_size: int


__all__ = [
    "KnowledgeBaseCreate",
    "KnowledgeBaseDeleteResponse",
    "KnowledgeBaseOut",
    "KnowledgeBasePage",
    "KnowledgeBaseUpdate",
]
