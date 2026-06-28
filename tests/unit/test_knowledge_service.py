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
from ragent.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
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
    """模拟 AsyncSession：flush / commit / refresh。"""

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def refresh(self, obj: Any) -> None:
        """模拟 DB refresh：回填 DB 默认列（created_at / updated_at）。"""
        now = datetime.datetime.now(datetime.UTC)
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
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

    async def add(self, kb: _FakeKB) -> None:
        """模拟 BaseRepository.add：写入内存索引。"""
        self._by_id[kb.id] = kb
        self._by_name[kb.name] = kb

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

    async def get_active_by_name(self, name: str) -> _FakeKB | None:
        kb = self._by_name.get(name)
        if kb is None:
            return None
        # 仅返回 active，archived 不算重名
        if kb.status != KnowledgeBaseStatus.ACTIVE.value:
            return None
        return kb


class _FakeVectorStore:
    """模拟 BaseVectorStore，仅实现 ensure_collection / drop_collection。"""

    def __init__(self, *, drop_raises: bool = False) -> None:
        self.drop_calls: list[str] = []
        self.ensure_calls: list[tuple[str, int]] = []
        self._drop_raises = drop_raises

    async def ensure_collection(self, collection_name: str, dim: int) -> None:
        self.ensure_calls.append((collection_name, dim))

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
    """删除知识库成功：状态归档 + 释放名称占用 + 调用 drop_collection。"""
    kb = _FakeKB(id="kb-1", name="del-me", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"del-me": kb})
    vector_store = _FakeVectorStore()
    service = _build_service(repo=repo, vector_store=vector_store)

    result = await service.delete_knowledge_base("kb-1")

    assert result.id == "kb-1"
    assert result.status == KnowledgeBaseStatus.ARCHIVED.value
    assert result.collection_name == "kb_1"
    assert kb.status == KnowledgeBaseStatus.ARCHIVED.value
    # 名称被释放：改为 __deleted__{id} 格式
    assert kb.name == "del-me__deleted__kb-1"
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
    """向量库 collection 删除失败：不抛异常，数据库仍归档且名称已释放。"""
    kb = _FakeKB(id="kb-1", name="del-me", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"del-me": kb})
    vector_store = _FakeVectorStore(drop_raises=True)
    service = _build_service(repo=repo, vector_store=vector_store)

    # 不应抛异常
    result = await service.delete_knowledge_base("kb-1")

    assert result.status == KnowledgeBaseStatus.ARCHIVED.value
    assert kb.status == KnowledgeBaseStatus.ARCHIVED.value
    assert kb.name == "del-me__deleted__kb-1"
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


# ---------- Delete releases name for recreate ----------


@pytest.mark.asyncio
async def test_delete_then_recreate_same_name_succeeds() -> None:
    """删除知识库后，重新创建同名知识库应成功（名称已释放）。"""
    kb = _FakeKB(id="kb-1", name="南京邮电大学", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": kb}, by_name={"南京邮电大学": kb})
    service = _build_service(repo=repo)

    # 删除
    delete_result = await service.delete_knowledge_base("kb-1")
    assert delete_result.status == KnowledgeBaseStatus.ARCHIVED.value
    assert kb.name == "南京邮电大学__deleted__kb-1"

    # 重新创建同名：不应报重名
    created = await service.create_knowledge_base(
        KnowledgeBaseCreate(name="南京邮电大学", embedding_dim=8, embedding_model="mock-embedding"),
    )
    assert created.name == "南京邮电大学"
    assert created.status == KnowledgeBaseStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_archived_same_name_does_not_block_create() -> None:
    """archived 旧记录占用某名称时，创建同名 active 知识库不应被拦截。"""
    archived_kb = _FakeKB(
        id="kb-old",
        name="taken-name",
        collection_name="kb_old",
        status=KnowledgeBaseStatus.ARCHIVED.value,
    )
    repo = _FakeKBRepo(by_id={"kb-old": archived_kb}, by_name={"taken-name": archived_kb})
    service = _build_service(repo=repo)

    created = await service.create_knowledge_base(
        KnowledgeBaseCreate(name="taken-name", embedding_dim=8, embedding_model="mock-embedding"),
    )
    assert created.name == "taken-name"


@pytest.mark.asyncio
async def test_create_duplicate_active_name_still_raises() -> None:
    """存在 active 同名记录时，创建仍应被拦截（回归保护）。"""
    active_kb = _FakeKB(id="kb-1", name="dup", collection_name="kb_1")
    repo = _FakeKBRepo(by_id={"kb-1": active_kb}, by_name={"dup": active_kb})
    service = _build_service(repo=repo)

    with pytest.raises(BizException) as exc_info:
        await service.create_knowledge_base(
            KnowledgeBaseCreate(name="dup", embedding_dim=8, embedding_model="mock-embedding"),
        )
    assert exc_info.value.code == 10101


@pytest.mark.asyncio
async def test_archived_same_name_does_not_block_update_rename() -> None:
    """重命名时，archived 旧记录的同名不应阻止 active 知识库使用该名。"""
    archived_kb = _FakeKB(
        id="kb-old",
        name="target-name",
        collection_name="kb_old",
        status=KnowledgeBaseStatus.ARCHIVED.value,
    )
    active_kb = _FakeKB(id="kb-1", name="current-name", collection_name="kb_1")
    repo = _FakeKBRepo(
        by_id={"kb-old": archived_kb, "kb-1": active_kb},
        by_name={"target-name": archived_kb, "current-name": active_kb},
    )
    service = _build_service(repo=repo)

    result = await service.update_knowledge_base(
        "kb-1",
        KnowledgeBaseUpdate(name="target-name"),
    )
    assert result.name == "target-name"
    assert active_kb.name == "target-name"


@pytest.mark.asyncio
async def test_update_duplicate_active_name_still_raises() -> None:
    """重命名为另一个 active 知识库的名称仍应被拦截（回归保护）。"""
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
    assert kb1.name == "old"


@pytest.mark.asyncio
async def test_delete_archived_name_truncation_to_max_length() -> None:
    """删除时归档名称超过 128 字符需截断，确保最终长度 == 128。"""
    # 构造一个超长名称，确保 suffix 会被前置截断
    long_name = "南京邮电大学" * 30  # 30 * 5 = 150 字符
    kb_id = "f6306940c46f4374a81fd552ee21babf"
    kb = _FakeKB(id=kb_id, name=long_name, collection_name="kb_1")
    repo = _FakeKBRepo(by_id={kb_id: kb}, by_name={long_name: kb})
    service = _build_service(repo=repo)

    await service.delete_knowledge_base(kb_id)

    assert kb.status == KnowledgeBaseStatus.ARCHIVED.value
    # 长度恰好为 128，且以 __deleted__{id} 结尾
    assert len(kb.name) == 128
    assert kb.name.endswith(f"__deleted__{kb_id}")


@pytest.mark.asyncio
async def test_build_archived_name_helper() -> None:
    """纯函数 _build_archived_name 行为校验。"""
    from ragent.service.knowledge_service import _build_archived_name

    # 常规名称
    assert _build_archived_name("南京邮电大学", "abc123") == "南京邮电大学__deleted__abc123"
    # 超长名称截断到 128
    long_name = "x" * 200
    result = _build_archived_name(long_name, "id1")
    assert len(result) == 128
    assert result.endswith("__deleted__id1")
    # 极端：原名称为空也安全（suffix 不会被截断）
    assert _build_archived_name("", "id2") == "__deleted__id2"
