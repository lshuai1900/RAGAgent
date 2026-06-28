"""领域枚举。

纯领域，零业务依赖。供 persistence / service / schemas 等层共享。
"""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    """文档状态机：pending → parsing → chunking → embedding → indexing → completed/failed。"""

    PENDING = "pending"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkEmbeddingStatus(StrEnum):
    """分块 Embedding 状态。"""

    PENDING = "pending"
    EMBEDDED = "embedded"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(StrEnum):
    """对话消息角色。"""

    USER = "user"
    ASSISTANT = "assistant"


class ProviderType(StrEnum):
    """模型供应商类型。"""

    QWEN = "qwen"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"


class KnowledgeBaseStatus(StrEnum):
    """知识库状态。"""

    ACTIVE = "active"
    ARCHIVED = "archived"
