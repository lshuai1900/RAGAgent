"""雪花 ID 生成器测试。

验证：唯一性、单调递增、字符串形式、worker_id 边界。
"""

from __future__ import annotations

import threading

from ragent.framework.core.snowflake import SnowflakeGenerator, generate_id


def test_generate_id_returns_string() -> None:
    """generate_id 返回字符串。"""
    snowflake_id = generate_id()
    assert isinstance(snowflake_id, str)
    assert snowflake_id.isdigit()
    assert int(snowflake_id) > 0


def test_ids_are_unique() -> None:
    """连续生成 10000 个 ID 全部唯一。"""
    ids = {generate_id() for _ in range(10000)}
    assert len(ids) == 10000


def test_ids_are_monotonic_increasing() -> None:
    """同一 generator 内 ID 单调递增。"""
    gen = SnowflakeGenerator(worker_id=1)
    prev = int(gen.next_id())
    for _ in range(100):
        curr = int(gen.next_id())
        assert curr > prev
        prev = curr


def test_thread_safety() -> None:
    """多线程并发生成 ID 全部唯一。"""
    gen = SnowflakeGenerator(worker_id=1)
    ids: set[str] = set()
    lock = threading.Lock()

    def _worker() -> None:
        local_ids = [gen.next_id() for _ in range(1000)]
        with lock:
            ids.update(local_ids)

    threads = [threading.Thread(target=_worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 8 * 1000 = 8000 个 ID 全部唯一
    assert len(ids) == 8000


def test_worker_id_boundary() -> None:
    """worker_id 边界：0 和 1023 合法，超出范围抛 ValueError。"""
    SnowflakeGenerator(worker_id=0)
    SnowflakeGenerator(worker_id=1023)
    try:
        SnowflakeGenerator(worker_id=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("worker_id=-1 应抛 ValueError")

    try:
        SnowflakeGenerator(worker_id=1024)
    except ValueError:
        pass
    else:
        raise AssertionError("worker_id=1024 应抛 ValueError")
