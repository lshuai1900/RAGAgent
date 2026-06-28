"""知识库 Repository。

依赖 domain（用枚举）+ persistence.models（用 ORM Model）+ BaseRepository。
service 层通过本 Repository 访问 t_knowledge_base 表，不直接写 ORM 查询。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.domain.enums import KnowledgeBaseStatus
from ragent.persistence.models.knowledge_base import KnowledgeBase
from ragent.persistence.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    """知识库 Repository。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeBase)

    async def get_by_id(self, id: str) -> KnowledgeBase | None:
        """按主键查询，自动过滤已归档。

        Args:
            id: 知识库 ID

        Returns:
            KnowledgeBase 或 None（不存在或已归档）
        """
        kb = await self._session.get(KnowledgeBase, id)
        if kb is None:
            return None
        if kb.status == KnowledgeBaseStatus.ARCHIVED.value:
            return None
        return kb

    async def get_by_id_strict(self, id: str) -> KnowledgeBase | None:
        """按主键查询，不过滤状态（管理后台用）。"""
        return await self._session.get(KnowledgeBase, id)

    async def get_by_name(self, name: str) -> KnowledgeBase | None:
        """按名称查询（含所有状态，含 archived）。

        Args:
            name: 知识库名称

        Returns:
            KnowledgeBase 或 None
        """
        stmt = select(KnowledgeBase).where(KnowledgeBase.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_name(self, name: str) -> KnowledgeBase | None:
        """按名称查询活跃知识库（仅 status == active）。

        用于创建/重命名时的重名校验：archived 的旧记录不阻止复用同名。

        Args:
            name: 知识库名称

        Returns:
            KnowledgeBase 或 None（无活跃同名记录时）
        """
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.name == name,
            KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[KnowledgeBase]:
        """列出所有活跃知识库。

        Args:
            limit: 每页大小
            offset: 偏移量

        Returns:
            活跃知识库列表（按创建时间降序）
        """
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE.value)
            .order_by(KnowledgeBase.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        """统计活跃知识库总数。"""
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(KnowledgeBase)
            .where(KnowledgeBase.status == KnowledgeBaseStatus.ACTIVE.value)
        )
        result = await self._session.execute(stmt)
        return int(result.scalar() or 0)

    async def increment_document_count(self, kb_id: str, delta: int = 1) -> None:
        """更新文档数（冗余计数）。

        Args:
            kb_id: 知识库 ID
            delta: 增量（+1 / -1）
        """
        kb = await self._session.get(KnowledgeBase, kb_id)
        if kb is not None:
            kb.document_count = max(0, kb.document_count + delta)
            await self._session.flush()


__all__ = ["KnowledgeBaseRepository"]
