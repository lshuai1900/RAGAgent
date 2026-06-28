"""KnowledgeService 更新 / 删除单元测试。

单元测试禁止真实 IO：DB / Milvus / Embedding 全部使用 Mock。
覆盖：
- 成功重命名知识库
- 重命名为已有名称时失败
- 更新不存在的知识库返回 404
- 删除知识库成功（归档 + 调用 drop_collection）
- 删除不存在知识库返回 404
- 删除时向量库 collection 删除失败不回滚数据库
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from ragent.domain.enums import KnowledgeBaseStatus
from ragent.framework.core.exceptions import BizException
from ragent.schemas.knowledge_base import KnowledgeBaseUpdate
from ragent.service.knowledge_service import KnowledgeService

# ---------- Fakes ----------


class _FakeKB:
    """内存知识库对象，模拟 ORM Model 属性。"""

    def __init__(
        self,
        *,
        id: str,
        name: str,
        description: str | None = None,
        collection_name: str = "kb_x",
        status: str = KnowledgeBaseStatus.ACTIVE.value,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.collection_name = collection_name
        self.embedding_dim = 8
        self.embedding_model = "mock-embedding"
        self.chunk_strategy = "recursive"
        self.chunk_size = 512
        self.chunk_overlap = 64
        self.document_count = 0
        self.status = status
        now = datetime.datetime.now(datetime.UTC)
        self.created_at = now
        self.updated_at = now


class _FakeSession:
    """模拟 AsyncSession：flush / commit / refresh 为空操作。"""

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, obj: Any) -> None:
        return None


class _FakeKBRepo:
    """模拟 KnowledgeBaseRepository。"""

    def __init__(
        self,
        *,
        by_id: dict[str, _FakeKB] | None = None,
        by_name: dict[str, _FakeKB] | None = None,
    ) -> None:
        self._by_id = by_id or {}
        self._by_name = by_name or {}
        self.session = _FakeSession()

    async def get_by_id(self, id: str) -> _FakeKB | None:
        kb = self._by_id.get(id)
        if kb is None:
            return None
        # 模拟真实 repo 行为：archived 视为不存在
        if kb.status == KnowledgeBaseStatus.ARCHIVED.value:
            return None
        return kb

    async def get_by_name(self, name: str) -> _FakeKB | None:
        return self._by_name.get(name)


class _FakeVectorStore:
    """模拟 BaseVectorStore，仅实现 drop_collection。"""

    def __init__(self, *, drop_raises: bool = False) -> None:
        self.drop_calls: list[str] = []
        self._drop_raises = drop_raises

    async def drop_collection(self, collection_name: str) -> None:
        self.drop_calls.append(collection_name)
        if self._drop_raises:
            raise RuntimeError("milvus drop failed")


class _MockEmbedding:
    """Mock Embedding 客户端（update/delete 不使用，仅满足构造函数）。"""

    def dim(self) -> int:
        return 8

    def model_name(self) -> str:
        return "mock-embedding"


def _build_service(
    *,
    repo: _FakeKBRepo,
    vector_store: _FakeVectorStore | None = None,
) -> KnowledgeService:
    return KnowledgeService(
        kb_repo=repo,  # type: ignore[arg-type]
        vector_store=vector_store or _FakeVectorStore(),  # type: ignore[arg-type]
        embedding_client=_MockEmbedding(),  # type: ignore[arg-type]
    )


# ---------- Update ----------


@pytest.mark.asyncio
async def test_update_rename_success() -> None:
    """成功重命名知识库。"""
    kb = _FakeKB(id="kb-1", name="old-name", description="old desc")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"old-name": kb})
    service = _build_service(repo=repo)

    result = await service.update_knowledge_base(
        "kb-1",
        KnowledgeBaseUpdate(name="new-name", description="new desc"),
    )

    assert result.name == "new-name"
    assert result.description == "new desc"
    assert kb.name == "new-name"
    assert kb.description == "new desc"


@pytest.mark.asyncio
async def test_update_rename_same_name_is_noop() -> None:
    """重命名为自身当前名称：不触发唯一性冲突，正常返回。"""
    kb = _FakeKB(id="kb-1", name="same")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"same": kb})
    service = _build_service(repo=repo)

    result = await service.update_knowledge_base("kb-1", KnowledgeBaseUpdate(name="same"))
    assert result.name == "same"


@pytest.mark.asyncio
async def test_update_duplicate_name_raises() -> None:
    """重命名为已有名称时失败：BizException code=10101。"""
    kb1 = _FakeKB(id="kb-1", name="old")
    kb2 = _FakeKB(id="kb-2", name="taken")
    repo = _FakeKBRepo(
        by_id={"kb-1": kb1, "kb-2": kb2},
        by_name={"old": kb1, "taken": kb2},
    )
    service = _build_service(repo=repo)

    with pytest.raises(BizException) as exc_info:
        await service.update_knowledge_base("kb-1", KnowledgeBaseUpdate(name="taken"))

    assert exc_info.value.code == 10101
    # 名称未被修改
    assert kb1.name == "old"


@pytest.mark.asyncio
async def test_update_not_found_returns_404() -> None:
    """更新不存在的知识库：BizException code=10404, http_status=404。"""
    repo = _FakeKBRepo()
    service = _build_service(repo=repo)

    with pytest.raises(BizException) as exc_info:
        await service.update_knowledge_base("nope", KnowledgeBaseUpdate(name="x"))

    assert exc_info.value.code == 10404
    assert exc_info.value.http_status == 404


# ---------- Delete ----------


@pytest.mark.asyncio
async def test_delete_success_archives_and_drops_collection() -> None:
    """删除知识库成功：状态归档 + 调用 drop_collection。"""
    kb = _FakeKB(id="kb-1", name="del-me", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"del-me": kb})
    vector_store = _FakeVectorStore()
    service = _build_service(repo=repo, vector_store=vector_store)

    result = await service.delete_knowledge_base("kb-1")

    assert result.id == "kb-1"
    assert result.status == KnowledgeBaseStatus.ARCHIVED.value
    assert result.collection_name == "kb_1"
    assert kb.status == KnowledgeBaseStatus.ARCHIVED.value
    assert vector_store.drop_calls == ["kb_1"]


@pytest.mark.asyncio
async def test_delete_not_found_returns_404() -> None:
    """删除不存在的知识库：BizException code=10404, http_status=404。"""
    repo = _FakeKBRepo()
    service = _build_service(repo=repo)

    with pytest.raises(BizException) as exc_info:
        await service.delete_knowledge_base("nope")

    assert exc_info.value.code == 10404
    assert exc_info.value.http_status == 404


@pytest.mark.asyncio
async def test_delete_drop_failure_does_not_rollback() -> None:
    """向量库 collection 删除失败：不抛异常，数据库仍归档。"""
    kb = _FakeKB(id="kb-1", name="del-me", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"del-me": kb})
    vector_store = _FakeVectorStore(drop_raises=True)
    service = _build_service(repo=repo, vector_store=vector_store)

    # 不应抛异常
    result = await service.delete_knowledge_base("kb-1")

    assert result.status == KnowledgeBaseStatus.ARCHIVED.value
    assert kb.status == KnowledgeBaseStatus.ARCHIVED.value
    assert vector_store.drop_calls == ["kb_1"]


@pytest.mark.asyncio
async def test_deleted_kb_not_visible_via_get_by_id() -> None:
    """删除后 get_by_id 视为不存在（archived 过滤），再次删除返回 404。"""
    kb = _FakeKB(id="kb-1", name="del-me", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"del-me": kb})
    service = _build_service(repo=repo)

    first = await service.delete_knowledge_base("kb-1")
    assert first.status == KnowledgeBaseStatus.ARCHIVED.value

    with pytest.raises(BizException) as exc_info:
        await service.delete_knowledge_base("kb-1")
    assert exc_info.value.code == 10404
    assert exc_info.value.http_status == 404
