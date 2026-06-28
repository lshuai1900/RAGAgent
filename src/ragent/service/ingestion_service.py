"""摄取 Service：编排文档上传 + Pipeline 异步触发。

职责：
- 上传文档：SHA256 去重、写 t_document（status=pending）、保存临时文件、通过 BackgroundTasks 触发 pipeline
- 异步执行 pipeline：parse → chunk → embed → index，更新 Document 状态机
- 查询文档：按 ID / 列表

文档状态机：
  pending → parsing → chunking → embedding → indexing → completed
                                                            ↘ failed（任何阶段失败）

约束：
- 使用 FastAPI BackgroundTasks（MVP 锁定，不引入 Celery/Dramatiq/Redis Queue）
- 任务失败只更新 Document.status = failed + error_message，不重试、不死信
- Pipeline 在独立 session 中运行（BackgroundTasks 与请求生命周期解耦）
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from fastapi import BackgroundTasks

from ragent.domain.enums import DocumentStatus
from ragent.framework.core.exceptions import BizException
from ragent.framework.core.logging import get_logger
from ragent.framework.core.snowflake import generate_id
from ragent.framework.db.session import get_session_factory
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.persistence.models.document import Document
from ragent.persistence.repositories.chunk_repo import DocumentChunkRepository
from ragent.persistence.repositories.document_repo import DocumentRepository
from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository
from ragent.schemas.document import DocumentOut, DocumentPage, DocumentUploadResponse

_logger = get_logger(__name__)

# 允许上传的文件类型（与 parser registry 支持类型保持一致）
_ALLOWED_FILE_TYPES = {"txt", "md", "markdown", "pdf"}
# 临时文件目录前缀（BackgroundTasks 执行完毕后清理）
_UPLOAD_DIR_PREFIX = "ragent_upload_"


class IngestionService:
    """摄取 Service：编排文档上传与 Pipeline 异步执行。"""

    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        document_repo: DocumentRepository,
        pipeline: IngestionPipeline,
    ) -> None:
        """初始化 IngestionService。

        Args:
            kb_repo: 知识库 Repository
            document_repo: 文档 Repository
            pipeline: 摄取 Pipeline（已注入 embedding_client / vector_store）
        """
        self._kb_repo = kb_repo
        self._document_repo = document_repo
        self._pipeline = pipeline

    async def upload_document(
        self,
        *,
        kb_id: str,
        filename: str,
        content: bytes,
        background_tasks: BackgroundTasks,
    ) -> DocumentUploadResponse:
        """上传文档：去重 + 写记录 + 触发异步 pipeline。

        流程：
        1. 校验知识库存在
        2. 校验文件类型
        3. 计算 SHA256
        4. 按 (kb_id, file_hash) 去重：若已存在直接返回（标记 duplicated=True）
        5. 写 t_document（status=pending）
        6. 保存临时文件
        7. 注册 BackgroundTask：异步执行 pipeline + 更新状态机
        8. 立即返回 document_id

        Args:
            kb_id: 知识库 ID
            filename: 原始文件名
            content: 文件二进制内容
            background_tasks: FastAPI BackgroundTasks

        Returns:
            DocumentUploadResponse 上传响应

        Raises:
            BizException: 知识库不存在 / 文件类型不支持
        """
        # 1. 校验知识库
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise BizException(
                message=f"知识库不存在: {kb_id}",
                code=10404,
            )

        # 2. 校验文件类型
        file_type = self._extract_file_type(filename)
        if file_type not in _ALLOWED_FILE_TYPES:
            raise BizException(
                message=(
                    f"不支持的文件类型: {file_type}，仅支持 "
                    f"{sorted(_ALLOWED_FILE_TYPES)}"
                ),
                code=10201,
            )

        # 3. 计算 SHA256
        file_hash = hashlib.sha256(content).hexdigest()
        file_size = len(content)

        # 4. 去重：(kb_id, file_hash) 命中则直接返回
        existing = await self._document_repo.get_by_hash(file_hash, kb_id)
        if existing is not None:
            _logger.info(
                "document_duplicated",
                kb_id=kb_id,
                document_id=existing.id,
                file_hash=file_hash,
            )
            return DocumentUploadResponse(
                document_id=existing.id,
                kb_id=kb_id,
                name=existing.name,
                file_type=existing.file_type,
                file_size=existing.file_size,
                file_hash=existing.file_hash,
                status=existing.status,
                duplicated=True,
            )

        # 5. 写 t_document（status=pending）
        document_id = generate_id()
        document = Document(
            id=document_id,
            kb_id=kb_id,
            name=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            status=DocumentStatus.PENDING.value,
            chunk_count=0,
            total_tokens=0,
            error_message=None,
        )
        await self._document_repo.add(document)
        # 更新 KB 文档计数
        await self._kb_repo.increment_document_count(kb_id, delta=1)
        await self._document_repo.session.commit()
        await self._document_repo.session.refresh(document)

        # 6. 保存临时文件（BackgroundTasks 执行完毕后由 _run_pipeline 清理）
        temp_dir = Path(tempfile.mkdtemp(prefix=_UPLOAD_DIR_PREFIX))
        # 保留原扩展名，便于 parser 推断
        suffix = Path(filename).suffix or f".{file_type}"
        temp_file_path = temp_dir / f"{document_id}{suffix}"
        # 同步写文件（小文件直接写，避免阻塞事件循环）
        temp_file_path.write_bytes(content)

        # 7. 注册 BackgroundTask：异步执行 pipeline + 更新状态机
        # 注意：BackgroundTask 在响应发送后执行，使用独立 session
        background_tasks.add_task(
            self._run_pipeline_async,
            kb_id=kb_id,
            document_id=document_id,
            collection_name=kb.collection_name,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            file_path=str(temp_file_path),
            file_type=file_type,
            temp_dir=str(temp_dir),
        )

        _logger.info(
            "document_uploaded",
            document_id=document_id,
            kb_id=kb_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
        )
        return DocumentUploadResponse(
            document_id=document_id,
            kb_id=kb_id,
            name=filename,
            file_type=file_type,
            file_size=file_size,
            file_hash=file_hash,
            status=document.status,
            duplicated=False,
        )

    async def get_document(self, document_id: str) -> DocumentOut:
        """按 ID 查询文档。

        Args:
            document_id: 文档 ID

        Returns:
            DocumentOut 响应

        Raises:
            BizException: 文档不存在
        """
        doc = await self._document_repo.get_by_id(document_id)
        if doc is None:
            raise BizException(
                message=f"文档不存在: {document_id}",
                code=10304,
            )
        return DocumentOut.model_validate(doc)

    async def list_documents(
        self,
        *,
        kb_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DocumentPage:
        """分页列出文档。

        Args:
            kb_id: 可选，按知识库过滤；None 时列出全部
            page: 页码（从 1 开始）
            page_size: 每页大小

        Returns:
            DocumentPage 分页响应
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        if kb_id is not None:
            items = await self._document_repo.list_by_kb(
                kb_id, limit=page_size, offset=offset
            )
            total = await self._document_repo.count_by_kb(kb_id)
        else:
            items = await self._document_repo.list_all(limit=page_size, offset=offset)
            total = await self._document_repo.count_all()

        return DocumentPage(
            items=[DocumentOut.model_validate(doc) for doc in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def _run_pipeline_async(
        self,
        *,
        kb_id: str,
        document_id: str,
        collection_name: str,
        chunk_size: int,
        chunk_overlap: int,
        file_path: str,
        file_type: str,
        temp_dir: str,
    ) -> None:
        """BackgroundTask：异步执行 pipeline 并更新状态机。

        使用独立 session（与请求 session 解耦）。
        任何阶段失败都标记 Document.status = failed + error_message。
        完成后清理临时文件。

        Args:
            kb_id: 知识库 ID
            document_id: 文档 ID
            collection_name: Milvus collection 名
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            file_path: 临时文件路径
            file_type: 文件类型
            temp_dir: 临时目录（执行完毕后清理）
        """
        # 使用独立 session factory（BackgroundTask 与请求生命周期解耦）
        session_factory = get_session_factory()
        path = Path(file_path)

        try:
            async with session_factory() as session:
                doc_repo = DocumentRepository(session)
                chunk_repo = DocumentChunkRepository(session)
                kb_repo = KnowledgeBaseRepository(session)

                # 1. parsing
                await doc_repo.update_status(
                    document_id, DocumentStatus.PARSING.value
                )
                await session.commit()
                parsed = await self._pipeline.parse(path, file_type)

                # 2. chunking
                await doc_repo.update_status(
                    document_id, DocumentStatus.CHUNKING.value
                )
                await session.commit()
                chunks = await self._pipeline.chunk(parsed, chunk_size, chunk_overlap)

                # 3. embedding
                await doc_repo.update_status(
                    document_id, DocumentStatus.EMBEDDING.value
                )
                await session.commit()
                vectors = await self._pipeline.embed(chunks)

                # 4. indexing（写 PostgreSQL 元数据 + Milvus 向量）
                await doc_repo.update_status(
                    document_id, DocumentStatus.INDEXING.value
                )
                await session.commit()

                # ensure collection（幂等，KB 创建时可能已建）
                kb = await kb_repo.get_by_id(kb_id)
                if kb is None:
                    raise BizException(
                        message=f"知识库不存在: {kb_id}",
                        code=10404,
                    )
                # 这里再次 ensure 防止 KB 创建时 Milvus 不可达
                await self._pipeline.vector_store.ensure_collection(
                    collection_name, kb.embedding_dim
                )

                indexed = await self._pipeline.index(
                    collection_name,
                    chunks,
                    vectors,
                    document_id=document_id,
                    kb_id=kb_id,
                    chunk_repo=chunk_repo,
                )

                # 5. completed：更新分块数与 token 数
                # ChunkDraft 无 token_count 字段，用 pipeline 内部估算逻辑累加
                total_tokens = sum(
                    IngestionPipeline._estimate_tokens(c.content) for c in chunks
                )
                await doc_repo.update_status(
                    document_id,
                    DocumentStatus.COMPLETED.value,
                    chunk_count=indexed,
                )
                # 更新 total_tokens
                doc = await doc_repo.get_by_id(document_id)
                if doc is not None:
                    doc.total_tokens = total_tokens
                await session.commit()

                _logger.info(
                    "pipeline_completed",
                    document_id=document_id,
                    kb_id=kb_id,
                    chunk_count=indexed,
                    total_tokens=total_tokens,
                )
        except Exception as exc:  # noqa: BLE001
            # 任务失败：仅更新 Document.status = failed + error_message，不重试
            _logger.error(
                "pipeline_failed",
                document_id=document_id,
                kb_id=kb_id,
                error=str(exc),
                exc_info=True,
            )
            try:
                async with session_factory() as session:
                    doc_repo = DocumentRepository(session)
                    await doc_repo.update_status(
                        document_id,
                        DocumentStatus.FAILED.value,
                        error_message=self._truncate_error(str(exc)),
                    )
                    await session.commit()
            except Exception as inner_exc:  # noqa: BLE001
                _logger.error(
                    "pipeline_failed_status_update_error",
                    document_id=document_id,
                    error=str(inner_exc),
                )
        finally:
            # 清理临时文件
            self._cleanup_temp(temp_dir, file_path)

    @staticmethod
    def _extract_file_type(filename: str) -> str:
        """从文件名提取扩展名（小写，无点）。"""
        suffix = Path(filename).suffix.lower().lstrip(".")
        # 标准化 markdown 别名
        if suffix == "markdown":
            return "md"
        return suffix

    @staticmethod
    def _truncate_error(message: str, max_length: int = 1000) -> str:
        """截断错误信息，避免数据库字段过长。"""
        if len(message) <= max_length:
            return message
        return message[:max_length] + "...[truncated]"

    @staticmethod
    def _cleanup_temp(temp_dir: str, file_path: str) -> None:
        """清理临时文件与目录。"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
            d = Path(temp_dir)
            if d.exists() and d.is_dir():
                # 目录应为空（已删除文件），直接 rmdir
                try:
                    d.rmdir()
                except OSError:
                    # 非空目录则用 shutil 兜底
                    import shutil

                    shutil.rmtree(d, ignore_errors=True)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("temp_cleanup_failed", path=file_path, error=str(exc))


__all__ = ["IngestionService"]
