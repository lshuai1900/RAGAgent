"""文档 API 路由。

约束：
- api 层只调用 service，不直接访问 repository / Milvus / EmbeddingClient
- 使用 schemas 做请求/响应模型
- 上传接口使用 FastAPI BackgroundTasks 异步触发 pipeline（立即返回 document_id）

接口：
- POST /api/v1/documents/upload：上传文档（multipart/form-data），异步触发摄取
- GET /api/v1/documents：分页列出文档（可按 kb_id 过滤）
- GET /api/v1/documents/{document_id}：按 ID 查询文档状态
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status

from ragent.api.deps import get_ingestion_service
from ragent.framework.core.exceptions import BizException
from ragent.framework.core.response import ApiResponse
from ragent.schemas.document import DocumentOut, DocumentPage, DocumentUploadResponse
from ragent.service.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

# 文件大小上限：50MB（MVP 限制，避免大文件拖垮 BackgroundTasks）
_MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post(
    "/upload",
    response_model=ApiResponse[DocumentUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    kb_id: str = Form(..., description="目标知识库 ID"),
    file: UploadFile = File(..., description="待上传文件（txt/md/pdf）"),
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentUploadResponse]:
    """上传文档：去重 + 写记录 + 异步触发摄取 pipeline。

    - 立即返回 document_id（status=pending）
    - 摄取在 BackgroundTasks 中执行：parse → chunk → embed → index
    - 文档状态可通过 GET /api/v1/documents/{document_id} 查询
    - 同一知识库下相同 SHA256 视为重复文件，直接返回已有 document_id
    """
    # 校验文件大小（避免 OOM）
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise BizException(
            message=f"文件大小超过限制: {len(content)} > {_MAX_FILE_SIZE} bytes",
            code=10202,
        )
    if not content:
        raise BizException(
            message="文件内容为空",
            code=10203,
        )

    filename = file.filename or "unknown.txt"
    response = await service.upload_document(
        kb_id=kb_id,
        filename=filename,
        content=content,
        background_tasks=background_tasks,
    )
    return ApiResponse.success(data=response)


@router.get(
    "",
    response_model=ApiResponse[DocumentPage],
    status_code=status.HTTP_200_OK,
)
async def list_documents(
    kb_id: str | None = Query(None, description="按知识库过滤（可选）"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentPage]:
    """分页列出文档（可按 kb_id 过滤）。"""
    result = await service.list_documents(kb_id=kb_id, page=page, page_size=page_size)
    return ApiResponse.success(data=result)


@router.get(
    "/{document_id}",
    response_model=ApiResponse[DocumentOut],
    status_code=status.HTTP_200_OK,
)
async def get_document(
    document_id: str,
    service: IngestionService = Depends(get_ingestion_service),
) -> ApiResponse[DocumentOut]:
    """按 ID 查询文档状态。

    可用于轮询文档摄取进度：pending → parsing → chunking → embedding → indexing → completed/failed
    """
    doc = await service.get_document(document_id)
    return ApiResponse.success(data=doc)


__all__ = ["router"]
