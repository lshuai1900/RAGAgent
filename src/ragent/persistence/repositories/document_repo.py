"""文档 Repository。

依赖 domain（用枚举）+ persistence.models（用 ORM Model）+ BaseRepository。
service 层通过本 Repository 访问 t_document 表。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.persistence.models.document import Document
from ragent.persistence.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """文档 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Document)

    async def get_by_hash(self, file_hash: str, kb_id: str) -> Document | None:
        """按文件 hash + 知识库 ID 查询（用于去重）。

        同一知识库下，相同 hash 视为重复文件。

        Args:
            file_hash: SHA256 文件 hash
            kb_id: 知识库 ID

        Returns:
            已存在的 Document 或 None
        """
        stmt = select(Document).where(
            Document.file_hash == file_hash,
            Document.kb_id == kb_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_kb(self, document_id: str, kb_id: str) -> Document | None:
        """按 ID + 知识库 ID 查询（kb 作用域内的文档操作用）。

        Args:
            document_id: 文档 ID
            kb_id: 知识库 ID

        Returns:
            Document 或 None（不存在或不属于该知识库）
        """
        stmt = select(Document).where(
            Document.id == document_id,
            Document.kb_id == kb_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name_in_kb(self, name: str, kb_id: str) -> Document | None:
        """按文件名 + 知识库 ID 查询（用于重命名重名校验）。

        Args:
            name: 文件名
            kb_id: 知识库 ID

        Returns:
            Document 或 None
        """
        stmt = select(Document).where(
            Document.name == name,
            Document.kb_id == kb_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_kb(
        self,
        kb_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Document]:
        """列出某知识库下的文档（按创建时间降序）。

        Args:
            kb_id: 知识库 ID
            limit: 每页大小
            offset: 偏移量

        Returns:
            文档列表
        """
        stmt = (
            select(Document)
            .where(Document.kb_id == kb_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_kb(self, kb_id: str) -> int:
        """统计某知识库下的文档数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Document).where(Document.kb_id == kb_id)
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def count_all(self) -> int:
        """统计全部文档数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Document)
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def update_status(
        self,
        document_id: str,
        status: str,
        *,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        """更新文档状态。

        Args:
            document_id: 文档 ID
            status: 新状态（DocumentStatus 枚举值）
            error_message: 失败原因（失败时设置）
            chunk_count: 分块数（completed 时设置）
        """
        doc = await self._session.get(Document, document_id)
        if doc is None:
            return
        doc.status = status
        if error_message is not None:
            doc.error_message = error_message
        if chunk_count is not None:
            doc.chunk_count = chunk_count
        await self._session.flush()


__all__ = ["DocumentRepository"]
