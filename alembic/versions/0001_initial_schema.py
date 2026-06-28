"""initial schema: 创建 7 张表

Revision ID: 0001
Revises:
Create Date: 2026-06-27

创建表：
  t_knowledge_base / t_document / t_document_chunk /
  t_chat_session / t_chat_message / t_trace_span（预留）/ t_model_provider
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _common_columns() -> list[sa.Column]:
    """公共字段列（id / created_at / updated_at / deleted_at）。"""
    return [
        sa.Column("id", sa.String(64), primary_key=True, comment="雪花 ID"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="更新时间",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
    ]


def upgrade() -> None:
    # 1. t_knowledge_base
    op.create_table(
        "t_knowledge_base",
        *_common_columns(),
        sa.Column("name", sa.String(128), nullable=False, comment="名称"),
        sa.Column("description", sa.String(512), nullable=True, comment="描述"),
        sa.Column("collection_name", sa.String(128), nullable=False, comment="Milvus collection 名"),
        sa.Column("embedding_dim", sa.Integer, nullable=False, comment="向量维度"),
        sa.Column("embedding_model", sa.String(64), nullable=False, comment="Embedding 模型标识"),
        sa.Column("chunk_strategy", sa.String(32), nullable=False, comment="分块策略"),
        sa.Column("chunk_size", sa.Integer, nullable=True, comment="分块大小"),
        sa.Column("chunk_overlap", sa.Integer, nullable=True, comment="分块重叠"),
        sa.Column("document_count", sa.Integer, nullable=True, comment="文档数"),
        sa.Column("status", sa.String(16), nullable=False, comment="状态"),
        sa.UniqueConstraint("name", name="uq_t_knowledge_base_name"),
    )

    # 2. t_document
    op.create_table(
        "t_document",
        *_common_columns(),
        sa.Column(
            "kb_id",
            sa.String(64),
            sa.ForeignKey("t_knowledge_base.id"),
            nullable=False,
            comment="所属知识库",
        ),
        sa.Column("name", sa.String(256), nullable=False, comment="文件名"),
        sa.Column("file_type", sa.String(16), nullable=False, comment="文件类型"),
        sa.Column("file_size", sa.Integer, nullable=False, comment="字节数"),
        sa.Column("file_hash", sa.String(64), nullable=False, comment="SHA256"),
        sa.Column("status", sa.String(16), nullable=False, comment="文档状态"),
        sa.Column("chunk_count", sa.Integer, nullable=True, comment="分块数"),
        sa.Column("total_tokens", sa.Integer, nullable=True, comment="估算 token 数"),
        sa.Column("error_message", sa.Text, nullable=True, comment="失败原因"),
    )
    op.create_index("ix_t_document_kb_id", "t_document", ["kb_id"])
    op.create_index("ix_t_document_file_hash", "t_document", ["file_hash"])
    op.create_index("ix_t_document_status", "t_document", ["status"])

    # 3. t_document_chunk
    op.create_table(
        "t_document_chunk",
        *_common_columns(),
        sa.Column(
            "document_id",
            sa.String(64),
            sa.ForeignKey("t_document.id"),
            nullable=False,
            comment="所属文档",
        ),
        sa.Column(
            "kb_id",
            sa.String(64),
            sa.ForeignKey("t_knowledge_base.id"),
            nullable=False,
            comment="所属知识库",
        ),
        sa.Column("content", sa.Text, nullable=False, comment="分块文本"),
        sa.Column("chunk_index", sa.Integer, nullable=False, comment="文档内序号"),
        sa.Column("token_count", sa.Integer, nullable=True, comment="token 数"),
        sa.Column("char_count", sa.Integer, nullable=True, comment="字符数"),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=True,
            comment="结构化元信息",
        ),
        sa.Column("embedding_status", sa.String(16), nullable=False, comment="Embedding 状态"),
    )
    op.create_index("ix_t_document_chunk_document_id", "t_document_chunk", ["document_id"])
    op.create_index("ix_t_document_chunk_kb_id", "t_document_chunk", ["kb_id"])
    op.create_index("ix_t_document_chunk_embedding_status", "t_document_chunk", ["embedding_status"])

    # 4. t_chat_session
    op.create_table(
        "t_chat_session",
        *_common_columns(),
        sa.Column("title", sa.String(128), nullable=True, comment="会话标题"),
        sa.Column(
            "kb_id",
            sa.String(64),
            sa.ForeignKey("t_knowledge_base.id"),
            nullable=True,
            comment="关联知识库",
        ),
        sa.Column("user_id", sa.String(64), nullable=True, comment="用户 ID"),
        sa.Column("message_count", sa.Integer, nullable=True, comment="消息数"),
        sa.Column("status", sa.String(16), nullable=False, comment="状态"),
    )
    op.create_index("ix_t_chat_session_kb_id", "t_chat_session", ["kb_id"])
    op.create_index("ix_t_chat_session_user_id", "t_chat_session", ["user_id"])

    # 5. t_chat_message
    op.create_table(
        "t_chat_message",
        *_common_columns(),
        sa.Column(
            "session_id",
            sa.String(64),
            sa.ForeignKey("t_chat_session.id"),
            nullable=False,
            comment="所属会话",
        ),
        sa.Column("role", sa.String(16), nullable=False, comment="角色"),
        sa.Column("content", sa.Text, nullable=False, comment="消息内容"),
        sa.Column(
            "retrieval_context",
            postgresql.JSONB,
            nullable=True,
            comment="关联检索结果摘要",
        ),
        sa.Column("trace_id", sa.String(64), nullable=True, comment="关联 trace_id"),
        sa.Column("token_count", sa.Integer, nullable=True, comment="token 数"),
        sa.Column("latency_ms", sa.Integer, nullable=True, comment="端到端耗时(ms)"),
    )
    op.create_index("ix_t_chat_message_session_id", "t_chat_message", ["session_id"])
    op.create_index("ix_t_chat_message_trace_id", "t_chat_message", ["trace_id"])

    # 6. t_trace_span（预留表，MVP 不写入数据）
    op.create_table(
        "t_trace_span",
        *_common_columns(),
        sa.Column("trace_id", sa.String(64), nullable=False, comment="Trace ID"),
        sa.Column("parent_id", sa.String(64), nullable=True, comment="父 Span ID"),
        sa.Column("node_name", sa.String(64), nullable=False, comment="节点名"),
        sa.Column("node_type", sa.String(16), nullable=False, comment="节点类型"),
        sa.Column("status", sa.String(16), nullable=False, comment="状态"),
        sa.Column("input_summary", postgresql.JSONB, nullable=True, comment="输入摘要"),
        sa.Column("output_summary", postgresql.JSONB, nullable=True, comment="输出摘要"),
        sa.Column("error_message", sa.Text, nullable=True, comment="错误信息"),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False, comment="开始时间"),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("duration_ms", sa.Integer, nullable=True, comment="耗时(ms)"),
    )
    op.create_index("ix_t_trace_span_trace_id", "t_trace_span", ["trace_id"])
    op.create_index("ix_t_trace_span_parent_id", "t_trace_span", ["parent_id"])

    # 7. t_model_provider
    op.create_table(
        "t_model_provider",
        *_common_columns(),
        sa.Column("name", sa.String(64), nullable=False, comment="供应商标识"),
        sa.Column("base_url", sa.String(256), nullable=False, comment="API 端点"),
        sa.Column("api_key_ref", sa.String(128), nullable=False, comment="密钥引用名"),
        sa.Column("chat_model", sa.String(64), nullable=False, comment="对话模型"),
        sa.Column("embedding_model", sa.String(64), nullable=False, comment="Embedding 模型"),
        sa.Column("embedding_dim", sa.Integer, nullable=False, comment="向量维度"),
        sa.Column("enabled", sa.Boolean, nullable=False, comment="是否启用"),
        sa.Column("priority", sa.Integer, nullable=False, comment="路由优先级"),
        sa.UniqueConstraint("name", name="uq_t_model_provider_name"),
    )


def downgrade() -> None:
    op.drop_table("t_model_provider")
    op.drop_table("t_trace_span")
    op.drop_table("t_chat_message")
    op.drop_table("t_chat_session")
    op.drop_table("t_document_chunk")
    op.drop_table("t_document")
    op.drop_table("t_knowledge_base")
