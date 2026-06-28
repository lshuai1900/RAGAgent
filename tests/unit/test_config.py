"""配置加载测试。

验证：YAML 加载、环境变量覆盖、嵌套配置结构。
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from ragent.framework.core.config import Settings, get_settings, reload_settings


@pytest.fixture(autouse=True)
def _isolate_settings() -> Iterator[None]:
    """每个测试前后清空 settings 缓存，避免相互污染。"""
    reload_settings()
    yield
    reload_settings()


def test_yaml_config_loaded() -> None:
    """默认从 configs/config.yaml 加载配置。"""
    settings = get_settings()
    assert settings.app.name == "ragent-py"
    assert settings.app.env == "dev"
    assert settings.db.pool_size == 10
    assert settings.embedding.dim == 1024
    assert settings.rag.default_top_k == 10


def test_env_var_overrides_yaml() -> None:
    """环境变量优先级高于 YAML。"""
    os.environ["RAGENT__APP__ENV"] = "test"
    os.environ["RAGENT__DB__POOL_SIZE"] = "5"
    try:
        reload_settings()
        settings = get_settings()
        assert settings.app.env == "test"
        assert settings.db.pool_size == 5
    finally:
        os.environ.pop("RAGENT__APP__ENV", None)
        os.environ.pop("RAGENT__DB__POOL_SIZE", None)


def test_plain_embedding_env_vars_override_yaml() -> None:
    """兼容直接使用 EMBEDDING_* 环境变量配置 OpenAI-compatible embedding 服务。"""
    os.environ["EMBEDDING_BASE_URL"] = "https://embedding.example.com/v1"
    os.environ["EMBEDDING_API_KEY"] = "test-key"
    os.environ["EMBEDDING_MODEL"] = "custom-embedding"
    os.environ["EMBEDDING_DIMENSION"] = "768"
    os.environ["EMBEDDING_BATCH_SIZE"] = "16"
    os.environ["EMBEDDING_TIMEOUT"] = "30"
    os.environ["EMBEDDING_SEND_DIMENSIONS"] = "true"
    try:
        reload_settings()
        settings = get_settings()
        assert settings.embedding.base_url == "https://embedding.example.com/v1"
        assert settings.embedding.api_key_ref == "EMBEDDING_API_KEY"
        assert settings.embedding.model == "custom-embedding"
        assert settings.embedding.dim == 768
        assert settings.embedding.batch_size == 16
        assert settings.embedding.timeout == 30
        assert settings.embedding.send_dimensions is True
    finally:
        for key in (
            "EMBEDDING_BASE_URL",
            "EMBEDDING_API_KEY",
            "EMBEDDING_MODEL",
            "EMBEDDING_DIMENSION",
            "EMBEDDING_BATCH_SIZE",
            "EMBEDDING_TIMEOUT",
            "EMBEDDING_SEND_DIMENSIONS",
        ):
            os.environ.pop(key, None)


def test_nested_config_structure() -> None:
    """配置嵌套结构完整。"""
    settings: Settings = get_settings()
    # 各 section 都应为对应配置对象
    assert hasattr(settings, "app")
    assert hasattr(settings, "db")
    assert hasattr(settings, "milvus")
    assert hasattr(settings, "llm")
    assert hasattr(settings, "embedding")
    assert hasattr(settings, "rag")
    # milvus.uri 应为非空字符串（具体值由 YAML 或环境变量决定）
    assert isinstance(settings.milvus.uri, str)
    assert len(settings.milvus.uri) > 0
