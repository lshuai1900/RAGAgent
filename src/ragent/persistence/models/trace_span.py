"""t_trace_span 链路追踪节点表 ORM Model。

★ 预留表：MVP 阶段仅建表结构，不写入任何 Span 数据。
MVP 仅实现 trace_id 透传 + X-Trace-Id 响应头 + 结构化日志。
复杂 Span 树 / @rag_trace_node / 可视化追踪留待 P7 生产特性阶段。
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ragent.persistence.models.base import Base, TimestampMixin


class TraceSpan(Base, TimestampMixin):
    """链路追踪节点（预留表，MVP 不写入数据）。"""

    __tablename__ = "t_trace_span"

    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="一次请求的 Trace ID")
    parent_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True, comment="父 Span ID（树形，MVP 不用）"
    )
    node_name: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="节点名（parse/chunk/embed/retrieve/llm_stream/sse_push）"
    )
    node_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="节点类型：ingestion/retrieval/generation/transport"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="running", comment="状态：running/success/failed"
    )
    input_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="输入摘要（截断）")
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, comment="输出摘要")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="开始时间")
    end_time: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="结束时间"
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="耗时(ms)")
