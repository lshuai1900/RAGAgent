"""雪花 ID 生成器。

生成 64 位整数 ID（字符串形式），结构：
  1 bit 符号位 | 41 bit 毫秒时间戳 | 10 bit worker_id | 12 bit 序列号

主键为 String 类型，由本模块生成雪花 ID。
"""

from __future__ import annotations

import threading
import time

# 自定义纪元（ms），减少时间戳位数占用
_EPOCH = 1_700_000_000_000

_WORKER_ID_BITS = 10
_SEQUENCE_BITS = 12
_MAX_WORKER_ID = (1 << _WORKER_ID_BITS) - 1  # 1023
_MAX_SEQUENCE = (1 << _SEQUENCE_BITS) - 1  # 4095

_WORKER_ID_SHIFT = _SEQUENCE_BITS
_TIMESTAMP_SHIFT = _SEQUENCE_BITS + _WORKER_ID_BITS


class SnowflakeGenerator:
    """雪花 ID 生成器（线程安全）。

    使用 threading.Lock 保护序列号计数器。生成操作为纯计算（无 IO），
    锁持有时间为微秒级，不会阻塞事件循环。
    SQLAlchemy 的 default 回调是同步调用，故本生成器为同步实现。
    """

    def __init__(self, worker_id: int = 1) -> None:
        if not 0 <= worker_id <= _MAX_WORKER_ID:
            raise ValueError(f"worker_id 必须在 0~{_MAX_WORKER_ID} 之间，当前: {worker_id}")
        self._worker_id = worker_id
        self._sequence = 0
        self._last_timestamp = -1
        self._lock = threading.Lock()

    def next_id(self) -> str:
        """生成下一个雪花 ID（字符串形式）。"""
        with self._lock:
            timestamp = self._current_ms()
            if timestamp == self._last_timestamp:
                self._sequence = (self._sequence + 1) & _MAX_SEQUENCE
                if self._sequence == 0:
                    # 同一毫秒序列号耗尽，等待下一毫秒
                    timestamp = self._wait_next_ms(timestamp)
            else:
                self._sequence = 0
            self._last_timestamp = timestamp

            snowflake = (
                (timestamp - _EPOCH) << _TIMESTAMP_SHIFT | (self._worker_id << _WORKER_ID_SHIFT) | self._sequence
            )
            return str(snowflake)

    @staticmethod
    def _current_ms() -> int:
        return int(time.time() * 1000)

    def _wait_next_ms(self, last_timestamp: int) -> int:
        """忙等到下一毫秒（仅在同毫秒生成 4096 个 ID 时触发，极端场景）。"""
        timestamp = self._current_ms()
        while timestamp <= last_timestamp:
            timestamp = self._current_ms()
        return timestamp


# 模块级单例（worker_id 默认 1，可通过环境变量 RAGENT__SNOWFLAKE__WORKER_ID 覆盖）
_generator = SnowflakeGenerator(worker_id=1)


def generate_id() -> str:
    """生成雪花 ID（供 ORM Model default 使用）。"""
    return _generator.next_id()


def configure_worker_id(worker_id: int) -> None:
    """重新配置 worker_id（应用启动时调用）。"""
    global _generator
    _generator = SnowflakeGenerator(worker_id=worker_id)
