"""泛型 BaseRepository：CRUD 基础方法。

service 层通过具体 Repository（继承本类）访问数据，不直接写 ORM 查询。
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.persistence.models.base import TimestampMixin

# 约束 ModelT 必须同时具备 Base 与 TimestampMixin 的能力（公共字段）
ModelT = TypeVar("ModelT", bound=TimestampMixin)


class BaseRepository(Generic[ModelT]):
    """泛型 Repository 基类，提供通用 CRUD 能力。

    具体 Repository 继承本类并指定 model，可覆写或扩展方法。
    """

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    @property
    def session(self) -> AsyncSession:
        """当前 DB session。"""
        return self._session

    @property
    def model(self) -> type[ModelT]:
        """当前 ORM Model 类。"""
        return self._model

    async def get_by_id(self, id: str) -> ModelT | None:
        """按主键查询。"""
        return await self._session.get(self._model, id)

    async def add(self, entity: ModelT) -> ModelT:
        """新增实体（需调用方 commit）。"""
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ModelT]:
        """分页查询（不含软删除过滤，MVP 不强制）。"""
        stmt = select(self._model).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, entity: ModelT) -> None:
        """删除实体（物理删除，软删除由调用方设置 deleted_at）。"""
        await self._session.delete(entity)
        await self._session.flush()

    async def soft_delete(self, entity: ModelT) -> ModelT:
        """软删除：设置 deleted_at。"""
        import datetime

        entity.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        return entity
