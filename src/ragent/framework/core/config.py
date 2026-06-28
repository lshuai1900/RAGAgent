"""配置加载：pydantic-settings + YAML。

配置来源优先级：环境变量 > configs/config.yaml > 代码默认值。
环境变量命名：RAGENT__{SECTION}__{KEY}（双下划线分隔，如 RAGENT__DB__URL）。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# 项目根目录（pyproject.toml 所在目录）
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_CONFIG_PATH = _PROJECT_ROOT / "configs" / "config.yaml"


class AppConfig(BaseModel):
    """应用配置。"""

    host: str = "0.0.0.0"
    port: int = 8000
    name: str = "ragent-py"
    env: str = "dev"


class DbConfig(BaseModel):
    """数据库配置。"""

    url: str = "postgresql+asyncpg://ragent:ragent@localhost:5432/ragent"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False


class MilvusConfig(BaseModel):
    """Milvus 配置。"""

    uri: str = "http://localhost:19530"


class LlmConfig(BaseModel):
    """LLM 配置。

    api_key_ref 为环境变量名（密钥不入库明文），实际密钥从环境变量读取。
    默认对齐 DashScope 兼容端点（qwen 系列）。
    """

    default_provider: str = "qwen"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key_ref: str = "QWEN_API_KEY"
    model: str = "qwen-plus"
    timeout: int = 60
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int | None = None


class EmbeddingConfig(BaseModel):
    """Embedding 配置。

    api_key_ref 为环境变量名（密钥不入库明文），实际密钥从环境变量读取。
    默认对齐 DashScope 兼容端点（qwen 系列）。
    """

    default_provider: str = "qwen"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key_ref: str = "QWEN_API_KEY"
    model: str = "text-embedding-v3"
    dim: int = 1024
    batch_size: int = 10
    timeout: int = 60


class RagConfig(BaseModel):
    """RAG 配置。"""

    default_top_k: int = 10


def _load_yaml_config() -> dict[str, Any]:
    """加载 configs/config.yaml，文件不存在时返回空 dict。"""
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class YamlConfigSource(PydanticBaseSettingsSource):
    """从 YAML 文件加载配置的 pydantic-settings 源。"""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)
        self._yaml_data: dict[str, Any] = _load_yaml_config()

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        value = self._yaml_data.get(field_name)
        return value, field_name, False

    def __call__(self) -> dict[str, Any]:
        return self._yaml_data


class Settings(BaseSettings):
    """全局配置。

    优先级：环境变量 > YAML > 默认值。
    """

    model_config = SettingsConfigDict(
        env_prefix="RAGENT__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    db: DbConfig = DbConfig()
    milvus: MilvusConfig = MilvusConfig()
    llm: LlmConfig = LlmConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    rag: RagConfig = RagConfig()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # 顺序即优先级：环境变量 > YAML > init > dotenv > secrets
        return (
            env_settings,
            YamlConfigSource(settings_cls),
            init_settings,
            dotenv_settings,
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """获取全局配置单例。"""
    return Settings()


def reload_settings() -> Settings:
    """重新加载配置（主要用于测试）。"""
    get_settings.cache_clear()
    return get_settings()
