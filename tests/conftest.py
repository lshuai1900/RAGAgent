"""pytest 全局 fixture。

- 单元测试不依赖外部服务（DB / Milvus / LLM 全 Mock）
- 集成测试依赖 docker-compose 启动的 PostgreSQL + Milvus
- LLM/Embedding 调用必须可 Mock
"""

from __future__ import annotations

import os
import socket
from collections.abc import AsyncIterator
from urllib.parse import urlparse

import pytest

from ragent.framework.core.config import reload_settings


def _is_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    """探测 TCP 端口是否可达。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _milvus_reachable() -> bool:
    """探测 Milvus 是否可达。"""
    from ragent.framework.core.config import get_settings

    uri = get_settings().milvus.uri
    parsed = urlparse(uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 19530
    return _is_reachable(host, port)


def _postgres_reachable() -> bool:
    """探测 PostgreSQL 是否可达。"""
    from ragent.framework.core.config import get_settings

    uri = get_settings().db.url
    try:
        if "://" in uri:
            _, rest = uri.split("://", 1)
        else:
            rest = uri
        if "@" in rest:
            _, host_port_db = rest.split("@", 1)
        else:
            host_port_db = rest
        host_port = host_port_db.split("/", 1)[0]
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host, port = host_port, 5432
    except Exception:  # noqa: BLE001
        return False
    return _is_reachable(host, port)


@pytest.fixture(autouse=True)
def _reset_settings() -> AsyncIterator[None]:
    """每个测试前重置 settings，避免相互污染。"""
    reload_settings()
    yield


@pytest.fixture
def milvus_available() -> bool:
    """Milvus 可达时返回 True，否则 pytest.skip。"""
    if not _milvus_reachable():
        pytest.skip("Milvus 不可达，跳过集成测试")
    return True


@pytest.fixture
def postgres_available() -> bool:
    """PostgreSQL 可达时返回 True，否则 pytest.skip。"""
    if not _postgres_reachable():
        pytest.skip("PostgreSQL 不可达，跳过集成测试")
    return True


@pytest.fixture
def qwen_api_key_set() -> bool:
    """QWEN_API_KEY 已设置时返回 True，否则 pytest.skip（避免真实调用）。"""
    if not os.environ.get("QWEN_API_KEY"):
        pytest.skip("QWEN_API_KEY 未设置，跳过真实 Embedding 集成测试")
    return True
