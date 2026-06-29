"""文档分块 Repository。

依赖 domain（用枚举）+ persistence.models（用 ORM Model）+ BaseRepository。
service 层通过本 Repository 访问 t_document_chunk 表。

注意：向量本身不入 PostgreSQL，存于 Milvus，以 chunk.id 关联。
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.domain.enums import ChunkEmbeddingStatus
from ragent.persistence.models.chunk import DocumentChunk
from ragent.persistence.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """文档分块 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DocumentChunk)

    async def add_batch(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """批量新增分块。

        Args:
            chunks: 分块 ORM 实体列表

        Returns:
            已 flush 的分块列表（含生成的 id）
        """
        for chunk in chunks:
            self._session.add(chunk)
        await self._session.flush()
        return chunks

    async def list_by_document(self, document_id: str) -> list[DocumentChunk]:
        """按文档 ID 列出所有分块（按 chunk_index 升序）。

        Args:
            document_id: 文档 ID

        Returns:
            分块列表
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_kb(
        self,
        kb_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DocumentChunk]:
        """按知识库 ID 列出分块。

        Args:
            kb_id: 知识库 ID
            limit: 每页大小
            offset: 偏移量

        Returns:
            分块列表
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.kb_id == kb_id)
            .order_by(DocumentChunk.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_document(self, document_id: str) -> int:
        """统计某文档的分块数。"""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def update_embedding_status(
        self,
        chunk_id: str,
        status: str,
    ) -> None:
        """更新分块 Embedding 状态。

        Args:
            chunk_id: 分块 ID
            status: 新状态（ChunkEmbeddingStatus 枚举值）
        """
        chunk = await self._session.get(DocumentChunk, chunk_id)
        if chunk is None:
            return
        chunk.embedding_status = status
        await self._session.flush()

    async def update_embedding_status_batch(
        self,
        chunk_ids: list[str],
        status: str,
    ) -> None:
        """批量更新分块 Embedding 状态。

        Args:
            chunk_ids: 分块 ID 列表
            status: 新状态
        """
        if not chunk_ids:
            return
        for chunk_id in chunk_ids:
            chunk = await self._session.get(DocumentChunk, chunk_id)
            if chunk is not None:
                chunk.embedding_status = status
        await self._session.flush()

    async def list_ids_by_document(self, document_id: str) -> list[str]:
        """列出某文档下所有分块的 ID（用于 Milvus 删除）。

        Args:
            document_id: 文档 ID

        Returns:
            分块 ID 列表
        """
        stmt = select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def delete_by_document(self, document_id: str) -> int:
        """删除某文档下的所有分块记录（物理删除）。

        用于删除文件 / 重新处理场景：先删向量库索引，再删 PG 分块元数据。

        Args:
            document_id: 文档 ID

        Returns:
            删除的行数
        """
        from sqlalchemy import delete as sa_delete

        stmt = sa_delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self._session.execute(stmt)
        # SQLAlchemy 2.0 静态类型不暴露 Result.rowcount，运行时实际存在；
        # DELETE/UPDATE 返回的是 CursorResult，cast 后 mypy 可识别 rowcount。
        cursor_result = cast(CursorResult[Any], result)
        return int(cursor_result.rowcount or 0)

    async def list_contents_by_document(self, document_id: str) -> list[dict[str, Any]]:
        """列出某文档所有分块的内容与元信息（供重新处理复用）。

        按创建顺序返回 content / chunk_index / chunk_metadata。

        Args:
            document_id: 文档 ID

        Returns:
            分块内容字典列表
        """
        stmt = (
            select(DocumentChunk.content, DocumentChunk.chunk_index, DocumentChunk.chunk_metadata)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self._session.execute(stmt)
        return [{"content": row[0], "chunk_index": row[1], "metadata": dict(row[2] or {})} for row in result.all()]

    async def get_metadata_for_index(self, document_id: str) -> list[dict[str, Any]]:
        """获取某文档所有分块的 metadata（供 Milvus 索引使用）。

        Args:
            document_id: 文档 ID

        Returns:
            metadata 字典列表（按 chunk_index 升序）
        """
        stmt = (
            select(DocumentChunk.id, DocumentChunk.chunk_metadata, DocumentChunk.content)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self._session.execute(stmt)
        return [{"id": row[0], "metadata": dict(row[1] or {}), "content": row[2]} for row in result.all()]


__all__ = [
    "ChunkEmbeddingStatus",
    "DocumentChunkRepository",
]
