"""知识库 API 路由。

约束：
- api 层只调用 service，不直接访问 repository / Milvus / EmbeddingClient
- 使用 schemas 做请求/响应模型
- 返回统一 ApiResponse[T]

接口：
- POST /api/v1/knowledge-bases：创建知识库
- GET /api/v1/knowledge-bases：分页列出知识库
- GET /api/v1/knowledge-bases/{kb_id}：按 ID 查询知识库
- PATCH /api/v1/knowledge-bases/{kb_id}：更新知识库（重命名 / 描述 / 状态）
- DELETE /api/v1/knowledge-bases/{kb_id}：删除知识库（软删除 + 清理向量库 collection）

知识库作用域文档管理接口（kb-scoped documents）：
- PATCH /api/v1/knowledge-bases/{kb_id}/documents/{document_id}：重命名文档
- DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id}：删除文档（同时删除向量索引）
- POST /api/v1/knowledge-bases/{kb_id}/documents/{document_id}/reprocess：重新处理文档
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status

from ragent.api.deps import get_ingestion_service, get_knowledge_service
from ragent.framework.core.response import ApiResponse
from ragent.schemas.document import (
    DocumentDeleteResponse,
    DocumentOut,
    DocumentUpdate,
)
from ragent.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseDeleteResponse,
    KnowledgeBaseOut,
    KnowledgeBasePage,
    KnowledgeBaseUpdate,
)
from ragent.service.ingestion_service import IngestionService
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


@router.patch(
    "/{kb_id}",
    response_model=ApiResponse[KnowledgeBaseOut],
    status_code=status.HTTP_200_OK,
)
async def update_knowledge_base(
    kb_id: str,
    payload: KnowledgeBaseUpdate,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ApiResponse[KnowledgeBaseOut]:
    """更新知识库（重命名 / 描述 / 状态）。

    - 部分更新：仅传入的字段会被修改
    - 名称变更时校验唯一性，重名返回 400
    - 知识库不存在返回 404
    """
    kb = await service.update_knowledge_base(kb_id, payload)
    return ApiResponse.success(data=kb)


@router.delete(
    "/{kb_id}",
    response_model=ApiResponse[KnowledgeBaseDeleteResponse],
    status_code=status.HTTP_200_OK,
)
async def delete_knowledge_base(
    kb_id: str,
    service: KnowledgeService = Depends(get_knowledge_service),
) -> ApiResponse[KnowledgeBaseDeleteResponse]:
    """删除知识库（软删除）。

    - 将知识库状态改为 archived，列表与详情不再返回
    - 同时尝试删除对应向量库 collection，失败仅记录日志，不回滚数据库
    - 知识库不存在返回 404
    """
    result = await service.delete_knowledge_base(kb_id)
    return ApiResponse.success(data=result, message="删除成功")


# ============================================================================
# 知识库作用域文档管理接口（kb-scoped documents）
# ============================================================================


@router.patch(
    "/{kb_id}/documents/{document_id}",
    response_model=ApiResponse[DocumentOut],
    status_code=status.HTTP_200_OK,
)
async def update_document(
    kb_id: str,
    document_id: str,
    payload: DocumentUpdate,
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentOut]:
    """重命名文档（同一知识库内文件名唯一）。

    - 校验知识库存在且未删除
    - 校验文档存在且属于该知识库
    - 同一知识库下不能与其他文档重名
    - 文档不存在返回 404
    - 同名文件返回 400
    - 文件名为空返回 422（Pydantic 校验）
    """
    doc = await service.update_document(
        kb_id=kb_id,
        document_id=document_id,
        payload=payload,
    )
    return ApiResponse.success(data=doc, message="文件已重命名")


@router.delete(
    "/{kb_id}/documents/{document_id}",
    response_model=ApiResponse[DocumentDeleteResponse],
    status_code=status.HTTP_200_OK,
)
async def delete_document(
    kb_id: str,
    document_id: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentDeleteResponse]:
    """删除文档（同时删除向量索引 + 分块元数据 + 文档记录）。

    - 校验知识库存在且未删除
    - 校验文档存在且属于该知识库
    - 删除 Milvus 向量索引（best-effort，失败仅日志）
    - 删除 PG 分块元数据 + 文档记录
    - 递减知识库文档计数
    - 文档不存在返回 404
    """
    result = await service.delete_document(kb_id=kb_id, document_id=document_id)
    return ApiResponse.success(data=result, message="文件已删除")


@router.post(
    "/{kb_id}/documents/{document_id}/reprocess",
    response_model=ApiResponse[DocumentOut],
    status_code=status.HTTP_200_OK,
)
async def reprocess_document(
    kb_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentOut]:
    """重新处理文档（删除旧向量 + 旧分块，重新 embedding + 索引）。

    - 复用已存储的分块内容重新 embedding（原始上传文件未持久化）
    - 状态置为 embedding，通过 BackgroundTask 异步重新索引
    - 文档不存在返回 404
    - 无可重新处理内容（未完成分块）返回 400
    """
    doc = await service.reprocess_document(
        kb_id=kb_id,
        document_id=document_id,
        background_tasks=background_tasks,
    )
    return ApiResponse.success(data=doc, message="已提交重新处理")


__all__ = ["router"]
