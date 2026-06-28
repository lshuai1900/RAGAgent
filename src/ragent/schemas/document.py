"""文档 API Schema（Pydantic v2）。

顶层独立，可依赖 domain（用枚举/DTO），不得被 domain 依赖。
严格与 SQLAlchemy ORM Model 分离。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    """文档响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    kb_id: str
    name: str
    file_type: str
    file_size: int
    file_hash: str
    status: str
    chunk_count: int
    total_tokens: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentPage(BaseModel):
    """文档分页响应。"""

    items: list[DocumentOut]
    total: int
    page: int
    page_size: int


class DocumentUploadResponse(BaseModel):
    """文档上传响应。"""

    document_id: str
    kb_id: str
    name: str
    file_type: str
    file_size: int
    file_hash: str
    status: str
    duplicated: bool = Field(False, description="是否为重复文件（hash 命中已有文档）")


class ChunkOut(BaseModel):
    """文档分块响应（可选查询）。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    kb_id: str
    content: str
    chunk_index: int
    token_count: int
    char_count: int
    metadata: dict[str, Any] = Field(default_factory=dict, alias="chunk_metadata")
    embedding_status: str
    created_at: datetime


__all__ = [
    "ChunkOut",
    "DocumentOut",
    "DocumentPage",
    "DocumentUploadResponse",
]
