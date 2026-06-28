"""t_model_provider 模型供应商配置表 ORM Model。"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ragent.persistence.models.base import Base, TimestampMixin


class ModelProvider(Base, TimestampMixin):
    """模型供应商配置。

    密钥只走环境变量，api_key_ref 存引用名不存明文。
    """

    __tablename__ = "t_model_provider"

    name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, comment="供应商标识（qwen/openai/deepseek）"
    )
    base_url: Mapped[str] = mapped_column(String(256), nullable=False, comment="API 端点")
    api_key_ref: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="密钥引用名（实际密钥从环境变量读，不入库明文）",
    )
    chat_model: Mapped[str] = mapped_column(String(64), nullable=False, comment="默认对话模型")
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False, comment="默认 Embedding 模型")
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False, comment="向量维度")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    priority: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="路由优先级（MVP 单供应商，预留）"
    )
