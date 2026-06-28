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
    # milvus.uri 默认值
    assert settings.milvus.uri == "http://localhost:19530"
