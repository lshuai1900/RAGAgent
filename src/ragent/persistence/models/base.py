"""ORM Model 基类：DeclarativeBase + 公共字段 mixin。

公共字段：id（雪花）/ created_at / updated_at / deleted_at。
表名 t_ 前缀。ORM Model 与 Pydantic Schema 严禁混用。
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ragent.framework.core.snowflake import generate_id


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base。"""


class TimestampMixin:
    """公共字段 mixin：id / created_at / updated_at / deleted_at。

    所有业务表通过继承此 mixin 获得统一公共字段。
    id 为 String 主键，默认值由雪花生成器产生。
    """

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=generate_id,
        comment="雪花 ID",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间",
    )
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="软删除时间（MVP 不强制过滤）",
    )
