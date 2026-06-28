"""知识库 Service：编排 KB CRUD + collection 创建。

职责：
- 创建知识库：生成唯一 collection_name，写 PostgreSQL，
  并调用 MilvusVectorStore.ensure_collection 创建 collection（幂等）
- 查询知识库：按 ID / 名称 / 分页列表
- 状态变更：active ↔ archived（MVP 仅提供基础切换）

不直接持有 DB session，依赖外部传入 repository。
不感知 HTTP 语义（异常由全局处理器转换为 ApiResponse）。
"""

from __future__ import annotations

from ragent.domain.enums import KnowledgeBaseStatus
from ragent.framework.core.exceptions import BizException
from ragent.framework.core.logging import get_logger
from ragent.framework.core.snowflake import generate_id
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.persistence.models.knowledge_base import KnowledgeBase
from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository
from ragent.rag.vector.base import BaseVectorStore
from ragent.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseDeleteResponse,
    KnowledgeBaseOut,
    KnowledgeBasePage,
    KnowledgeBaseUpdate,
)

_logger = get_logger(__name__)

# Milvus collection 名前缀 + 长度限制（必须以字母开头，仅含字母数字下划线）
_COLLECTION_PREFIX = "kb_"

# 知识库不存在错误码（HTTP 404）
_KB_NOT_FOUND_CODE = 10404
_KB_NOT_FOUND_HTTP_STATUS = 404

# name 字段最大长度（与 t_knowledge_base.name 列约束一致）
_KB_NAME_MAX_LENGTH = 128
# 归档名称后缀，软删除时释放原名称占用，避免阻止同名重建
_ARCHIVED_NAME_SUFFIX = "__deleted__"


def _build_archived_name(original_name: str, kb_id: str) -> str:
    """生成归档名称，释放原名称占用。

    格式：``{原名称截断}__deleted__{kb_id}``，总长度不超过 ``_KB_NAME_MAX_LENGTH``。

    Args:
        original_name: 原知识库名称
        kb_id: 知识库 ID

    Returns:
        归档后的名称（唯一，不会与 active 记录冲突）
    """
    suffix = f"{_ARCHIVED_NAME_SUFFIX}{kb_id}"
    max_original_len = _KB_NAME_MAX_LENGTH - len(suffix)
    truncated = original_name[: max(0, max_original_len)]
    return f"{truncated}{suffix}"


class KnowledgeService:
    """知识库 Service：编排 KB CRUD 与 Milvus collection 创建。"""

    def __init__(
        self,
        *,
        kb_repo: KnowledgeBaseRepository,
        vector_store: BaseVectorStore,
        embedding_client: BaseEmbeddingClient,
    ) -> None:
        """初始化 KnowledgeService。

        Args:
            kb_repo: 知识库 Repository
            vector_store: 向量库（用于 ensure_collection）
            embedding_client: Embedding 客户端（用于读取 dim/model_name）
        """
        self._kb_repo = kb_repo
        self._vector_store = vector_store
        self._embedding_client = embedding_client

    async def create_knowledge_base(self, payload: KnowledgeBaseCreate) -> KnowledgeBaseOut:
        """创建知识库。

        流程：
        1. 名称唯一性校验
        2. 生成 collection_name（kb_ + 雪花 ID，确保唯一且符合 Milvus 命名规则）
        3. 写 PostgreSQL
        4. 调用 MilvusVectorStore.ensure_collection 创建 collection（幂等）
        5. commit 后返回响应

        Args:
            payload: 创建请求

        Returns:
            KnowledgeBaseOut 响应

        Raises:
            BizException: 名称已存在 / Embedding 维度与配置不一致
        """
        # 1. 名称唯一性校验（仅校验 active 知识库，archived 旧记录不阻止复用同名）
        existing = await self._kb_repo.get_active_by_name(payload.name)
        if existing is not None:
            raise BizException(
                message=f"知识库名称已存在: {payload.name}",
                code=10101,
            )

        # 2. 维度一致性校验（防止与 Embedding 客户端配置不一致）
        if payload.embedding_dim != self._embedding_client.dim():
            raise BizException(
                message=(
                    f"embedding_dim({payload.embedding_dim}) 与 Embedding 客户端维度"
                    f"({self._embedding_client.dim()}) 不一致"
                ),
                code=10102,
            )

        # 3. 生成 collection_name（kb_ + 雪花 ID，确保唯一且 Milvus 合法）
        kb_id = generate_id()
        collection_name = f"{_COLLECTION_PREFIX}{kb_id}"

        # 4. 写 PostgreSQL
        kb = KnowledgeBase(
            id=kb_id,
            name=payload.name,
            description=payload.description,
            collection_name=collection_name,
            embedding_dim=payload.embedding_dim,
            embedding_model=payload.embedding_model,
            chunk_strategy=payload.chunk_strategy,
            chunk_size=payload.chunk_size,
            chunk_overlap=payload.chunk_overlap,
            document_count=0,
            status=KnowledgeBaseStatus.ACTIVE.value,
        )
        await self._kb_repo.add(kb)
        await self._kb_repo.session.commit()
        await self._kb_repo.session.refresh(kb)

        # 5. 创建 Milvus collection（幂等，失败不影响 KB 记录；后续上传时会再次 ensure）
        try:
            await self._vector_store.ensure_collection(collection_name, payload.embedding_dim)
        except Exception as exc:  # noqa: BLE001
            # collection 创建失败仅记录日志，不回滚 KB（上传时再次 ensure）
            _logger.warning(
                "milvus_ensure_collection_failed_on_kb_create",
                kb_id=kb_id,
                collection_name=collection_name,
                error=str(exc),
            )

        _logger.info(
            "knowledge_base_created",
            kb_id=kb_id,
            name=payload.name,
            collection_name=collection_name,
            embedding_dim=payload.embedding_dim,
        )
        return KnowledgeBaseOut.model_validate(kb)

    async def get_knowledge_base(self, kb_id: str) -> KnowledgeBaseOut:
        """按 ID 查询知识库。

        Args:
            kb_id: 知识库 ID

        Returns:
            KnowledgeBaseOut 响应

        Raises:
            BizException: 知识库不存在或已归档
        """
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise BizException(
                message=f"知识库不存在: {kb_id}",
                code=10404,
            )
        return KnowledgeBaseOut.model_validate(kb)

    async def list_knowledge_bases(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> KnowledgeBasePage:
        """分页列出活跃知识库。

        Args:
            page: 页码（从 1 开始）
            page_size: 每页大小

        Returns:
            KnowledgeBasePage 分页响应
        """
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        items = await self._kb_repo.list_active(limit=page_size, offset=offset)
        total = await self._kb_repo.count_active()

        return KnowledgeBasePage(
            items=[KnowledgeBaseOut.model_validate(kb) for kb in items],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_knowledge_base(
        self,
        kb_id: str,
        payload: KnowledgeBaseUpdate,
    ) -> KnowledgeBaseOut:
        """更新知识库（重命名 / 描述 / 状态）。

        部分更新语义：仅传入的字段会被修改。

        流程：
        1. 校验知识库存在（不存在返回 404）
        2. 名称变更时校验唯一性（与其他知识库重名则拒绝）
        3. 写 PostgreSQL
        4. 返回更新后的知识库

        Args:
            kb_id: 知识库 ID
            payload: 更新请求（name / description / status，均可选）

        Returns:
            KnowledgeBaseOut 响应

        Raises:
            BizException: 知识库不存在（404）/ 名称已存在（400）
        """
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise BizException(
                message=f"知识库不存在: {kb_id}",
                code=_KB_NOT_FOUND_CODE,
                http_status=_KB_NOT_FOUND_HTTP_STATUS,
            )

        # 名称变更：校验唯一性（仅校验 active，archived 旧记录不阻止复用同名）
        if payload.name is not None and payload.name != kb.name:
            existing = await self._kb_repo.get_active_by_name(payload.name)
            if existing is not None and existing.id != kb_id:
                raise BizException(
                    message=f"知识库名称已存在: {payload.name}",
                    code=10101,
                )
            kb.name = payload.name

        if payload.description is not None:
            kb.description = payload.description

        if payload.status is not None:
            kb.status = payload.status.value

        await self._kb_repo.session.flush()
        await self._kb_repo.session.commit()
        await self._kb_repo.session.refresh(kb)

        _logger.info(
            "knowledge_base_updated",
            kb_id=kb_id,
            name=kb.name,
        )
        return KnowledgeBaseOut.model_validate(kb)

    async def delete_knowledge_base(self, kb_id: str) -> KnowledgeBaseDeleteResponse:
        """删除知识库（软删除：归档 + 尝试删除向量库 collection）。

        流程：
        1. 校验知识库存在（不存在返回 404）
        2. 软删除：status → archived，提交 PostgreSQL
        3. 尝试删除 Milvus collection（失败仅记录日志，不回滚 DB）
        4. 返回删除响应

        Args:
            kb_id: 知识库 ID

        Returns:
            KnowledgeBaseDeleteResponse 响应

        Raises:
            BizException: 知识库不存在（404）
        """
        kb = await self._kb_repo.get_by_id(kb_id)
        if kb is None:
            raise BizException(
                message=f"知识库不存在: {kb_id}",
                code=_KB_NOT_FOUND_CODE,
                http_status=_KB_NOT_FOUND_HTTP_STATUS,
            )

        collection_name = kb.collection_name
        kb_name = kb.name

        # 1. 软删除（归档）：status → archived，并释放原名称占用（改名为 __deleted__{id}），
        #    避免原名称阻止后续重建同名知识库。先提交 DB，确保后续 collection 删除失败也不回滚。
        archived_name = _build_archived_name(kb_name, kb_id)
        kb.status = KnowledgeBaseStatus.ARCHIVED.value
        kb.name = archived_name
        await self._kb_repo.session.flush()
        await self._kb_repo.session.commit()

        _logger.info(
            "knowledge_base_archived",
            kb_id=kb_id,
            name=kb_name,
            archived_name=archived_name,
            collection_name=collection_name,
        )

        # 2. 尝试删除 Milvus collection（失败仅记录日志，不影响已归档状态）
        try:
            await self._vector_store.drop_collection(collection_name)
        except Exception as exc:  # noqa: BLE001
            _logger.warning(
                "milvus_drop_collection_failed_on_kb_delete",
                kb_id=kb_id,
                collection_name=collection_name,
                error=str(exc),
            )

        return KnowledgeBaseDeleteResponse(
            id=kb_id,
            status=KnowledgeBaseStatus.ARCHIVED.value,
            collection_name=collection_name,
        )


__all__ = ["KnowledgeService"]
