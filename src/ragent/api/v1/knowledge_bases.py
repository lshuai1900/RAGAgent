"""知识库 API 路由。

约束：
- api 层只调用 service，不直接访问 repository / Milvus / EmbeddingClient
- 使用 schemas 做请求/响应模型
- 返回统一 ApiResponse[T]

接口：
- POST /api/v1/knowledge-bases：创建知识库
- GET /api/v1/knowledge-bases：分页列出知识库
- GET /api/v1/knowledge-bases/{kb_id}：按 ID 查询知识库
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from ragent.api.deps import get_knowledge_service
from ragent.framework.core.response import ApiResponse
from ragent.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBasePage,
)
from ragent.service.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])


@router.post(
    "",
    response_model=ApiResponse[KnowledgeBaseOut],
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ApiResponse[KnowledgeBaseOut]:
    """创建知识库。

    - 名称全局唯一
    - 自动生成 Milvus collection（kb_<雪花ID>）
    - embedding_dim 必须与 Embedding 客户端配置一致
    """
    kb = await service.create_knowledge_base(payload)
    return ApiResponse.success(data=kb)


@router.get(
    "",
    response_model=ApiResponse[KnowledgeBasePage],
    status_code=status.HTTP_200_OK,
)
async def list_knowledge_bases(
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ApiResponse[KnowledgeBasePage]:
    """分页列出活跃知识库。"""
    result = await service.list_knowledge_bases(page=page, page_size=page_size)
    return ApiResponse.success(data=result)


@router.get(
    "/{kb_id}",
    response_model=ApiResponse[KnowledgeBaseOut],
    status_code=status.HTTP_200_OK,
)
async def get_knowledge_base(
    kb_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ApiResponse[KnowledgeBaseOut]:
    """按 ID 查询知识库。"""
    kb = await service.get_knowledge_base(kb_id)
    return ApiResponse.success(data=kb)


__all__ = ["router"]
