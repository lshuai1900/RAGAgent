"""IngestionService 文档管理（重命名 / 删除 / 重新处理）单元测试。

单元测试禁止真实 IO：DB / Milvus / Embedding 全部使用 Mock。

覆盖用户验收要求中的 8 个用例：
1. 重命名已入库文件成功
2. 重命名为同知识库内已有文件名失败（code=10301）
3. 删除已入库文件成功
4. 删除文件后列表不再返回该文件（验证 repo.delete 被调用 + KB 计数递减）
5. 删除文件后对应向量索引被删除（验证 vector_store.delete_by_document 被调用）
6. 重新处理已入库文件成功（验证状态置 embedding + BackgroundTask 注册 + 旧向量/分块删除）
7. 删除不存在文件返回 404（code=10304）
8. 操作不属于当前知识库的 document 返回 404（code=10304）
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from ragent.domain.enums import DocumentStatus
from ragent.framework.core.exceptions import BizException
from ragent.schemas.document import DocumentUpdate
from ragent.service.ingestion_service import IngestionService

# ---------- Fakes ----------


class _FakeSession:
    """模拟 AsyncSession：flush / commit / refresh / delete。"""

    def __init__(self) -> None:
        self.deleted: list[Any] = []
        self.commits = 0

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1
        return None

    async def refresh(self, obj: Any) -> None:
        now = datetime.datetime.now(datetime.UTC)
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now
        return None

    async def delete(self, obj: Any) -> None:
        self.deleted.append(obj)
        return None


class _FakeDoc:
    """内存文档对象，模拟 ORM Model 属性。"""

    def __init__(
        self,
        *,
        id: str,
        kb_id: str,
        name: str,
        file_type: str = "md",
        file_size: int = 100,
        file_hash: str = "hash-1",
        status: str = DocumentStatus.COMPLETED.value,
        chunk_count: int = 2,
        total_tokens: int = 50,
        error_message: str | None = None,
    ) -> None:
        self.id = id
        self.kb_id = kb_id
        self.name = name
        self.file_type = file_type
        self.file_size = file_size
        self.file_hash = file_hash
        self.status = status
        self.chunk_count = chunk_count
        self.total_tokens = total_tokens
        self.error_message = error_message
        now = datetime.datetime.now(datetime.UTC)
        self.created_at = now
        self.updated_at = now


class _FakeKB:
    """内存知识库对象。"""

    def __init__(
        self,
        *,
        id: str,
        name: str = "kb",
        collection_name: str = "kb_1",
        embedding_dim: int = 8,
        document_count: int = 1,
    ) -> None:
        self.id = id
        self.name = name
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.document_count = document_count


class _FakeDocRepo:
    """模拟 DocumentRepository。"""

    def __init__(
        self,
        *,
        session: _FakeSession,
        by_id: dict[str, _FakeDoc] | None = None,
        by_id_and_kb: dict[tuple[str, str], _FakeDoc] | None = None,
        by_name_in_kb: dict[tuple[str, str], _FakeDoc] | None = None,
    ) -> None:
        self.session = session
        self._by_id = by_id or {}
        self._by_id_and_kb = by_id_and_kb or {}
        self._by_name_in_kb = by_name_in_kb or {}
        self.status_updates: list[tuple[str, str, str | None, int | None]] = []
        self.deleted: list[_FakeDoc] = []

    async def get_by_id(self, document_id: str) -> _FakeDoc | None:
        return self._by_id.get(document_id)

    async def get_by_id_and_kb(self, document_id: str, kb_id: str) -> _FakeDoc | None:
        return self._by_id_and_kb.get((document_id, kb_id))

    async def get_by_name_in_kb(self, name: str, kb_id: str) -> _FakeDoc | None:
        return self._by_name_in_kb.get((name, kb_id))

    async def update_status(
        self,
        document_id: str,
        status: str,
        *,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        self.status_updates.append((document_id, status, error_message, chunk_count))
        # 同步更新内存对象状态（供 reprocess 末尾 get_by_id 返回最新状态）
        doc = self._by_id.get(document_id)
        if doc is not None:
            doc.status = status
            if error_message is not None:
                doc.error_message = error_message
            if chunk_count is not None:
                doc.chunk_count = chunk_count

    async def delete(self, doc: _FakeDoc) -> None:
        self.deleted.append(doc)
        # 从内存索引移除（模拟删除后 get_by_id 返回 None）
        self._by_id.pop(doc.id, None)
        await self.session.delete(doc)


class _FakeChunkRepo:
    """模拟 DocumentChunkRepository。"""

    def __init__(
        self,
        *,
        contents: list[dict[str, Any]] | None = None,
    ) -> None:
        self.delete_calls: list[str] = []
        self._contents = contents or []

    async def delete_by_document(self, document_id: str) -> int:
        self.delete_calls.append(document_id)
        return len(self._contents)

    async def list_contents_by_document(self, document_id: str) -> list[dict[str, Any]]:
        return list(self._contents)


class _FakeKBRepo:
    """模拟 KnowledgeBaseRepository（仅 document_count 增减用）。"""

    def __init__(self, *, by_id: dict[str, _FakeKB] | None = None) -> None:
        self._by_id = by_id or {}
        self.count_deltas: list[tuple[str, int]] = []

    async def get_by_id(self, kb_id: str) -> _FakeKB | None:
        return self._by_id.get(kb_id)

    async def increment_document_count(self, kb_id: str, delta: int = 1) -> None:
        self.count_deltas.append((kb_id, delta))
        kb = self._by_id.get(kb_id)
        if kb is not None:
            kb.document_count = max(0, kb.document_count + delta)


class _FakeVectorStore:
    """模拟 BaseVectorStore，仅记录 delete_by_document 调用。"""

    def __init__(self, *, delete_raises: bool = False) -> None:
        self.delete_calls: list[tuple[str, str]] = []
        self._delete_raises = delete_raises

    async def delete_by_document(self, collection_name: str, document_id: str) -> int:
        self.delete_calls.append((collection_name, document_id))
        if self._delete_raises:
            raise RuntimeError("milvus delete failed")
        return 1

    async def ensure_collection(self, collection_name: str, dim: int) -> None:
        return None


class _FakePipeline:
    """模拟 IngestionPipeline（仅暴露 vector_store 属性）。"""

    def __init__(self, vector_store: _FakeVectorStore) -> None:
        self.vector_store = vector_store


class _RecordingBackgroundTasks:
    """模拟 FastAPI BackgroundTasks：记录 add_task 调用，不执行。"""

    def __init__(self) -> None:
        self.tasks: list[tuple[Any, dict[str, Any]]] = []

    def add_task(self, func: Any, **kwargs: Any) -> None:
        self.tasks.append((func, kwargs))


def _build_service(
    *,
    doc_repo: _FakeDocRepo,
    kb_repo: _FakeKBRepo,
    vector_store: _FakeVectorStore | None = None,
    chunk_repo: _FakeChunkRepo | None = None,
) -> IngestionService:
    vs = vector_store or _FakeVectorStore()
    pipeline = _FakePipeline(vs)  # type: ignore[arg-type]
    return IngestionService(
        kb_repo=kb_repo,  # type: ignore[arg-type]
        document_repo=doc_repo,  # type: ignore[arg-type]
        pipeline=pipeline,  # type: ignore[arg-type]
        chunk_repo=chunk_repo,  # type: ignore[arg-type]
    )


# ---------- 1. 重命名成功 ----------


@pytest.mark.asyncio
async def test_rename_completed_document_success() -> None:
    """用例 1：重命名已入库文件成功。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="old.md", status=DocumentStatus.COMPLETED.value)
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
        by_name_in_kb={},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    result = await service.update_document(
        kb_id="kb-1",
        document_id="doc-1",
        payload=DocumentUpdate(filename="new.md"),
    )

    assert result.name == "new.md"
    assert doc.name == "new.md"


# ---------- 2. 重命名同名失败 ----------


@pytest.mark.asyncio
async def test_rename_to_duplicate_name_in_same_kb_raises() -> None:
    """用例 2：重命名为同知识库内已有文件名失败（code=10301）。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="old.md")
    other = _FakeDoc(id="doc-2", kb_id="kb-1", name="taken.md")
    kb = _FakeKB(id="kb-1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc, "doc-2": other},
        by_id_and_kb={("doc-1", "kb-1"): doc},
        # 同名查询返回 other 文档
        by_name_in_kb={("taken.md", "kb-1"): other},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.update_document(
            kb_id="kb-1",
            document_id="doc-1",
            payload=DocumentUpdate(filename="taken.md"),
        )

    assert exc_info.value.code == 10301
    # 名称未被修改
    assert doc.name == "old.md"


# ---------- 3. 删除已入库文件成功 ----------


@pytest.mark.asyncio
async def test_delete_completed_document_success() -> None:
    """用例 3：删除已入库文件成功（DB 删除 + 计数递减）。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="del.md", status=DocumentStatus.COMPLETED.value)
    kb = _FakeKB(id="kb-1", collection_name="kb_1", document_count=1)
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    vector_store = _FakeVectorStore()
    chunk_repo = _FakeChunkRepo()
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )

    result = await service.delete_document(kb_id="kb-1", document_id="doc-1")

    assert result.id == "doc-1"
    assert result.kb_id == "kb-1"
    # 文档记录被删除
    assert doc_repo.deleted == [doc]
    # KB 计数递减 1
    assert kb_repo.count_deltas == [("kb-1", -1)]
    assert kb.document_count == 0


# ---------- 4. 删除后列表不再返回该文件 ----------


@pytest.mark.asyncio
async def test_delete_document_removes_from_repo() -> None:
    """用例 4：删除后 get_by_id 返回 None（列表不再返回该文件）。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="del.md")
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    chunk_repo = _FakeChunkRepo()
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        chunk_repo=chunk_repo,
    )

    await service.delete_document(kb_id="kb-1", document_id="doc-1")

    # 删除后内存索引已移除，模拟 list 接口不再返回
    assert await doc_repo.get_by_id("doc-1") is None


# ---------- 5. 删除文件后对应向量索引被删除 ----------


@pytest.mark.asyncio
async def test_delete_document_calls_vector_store_delete_by_document() -> None:
    """用例 5：删除文件时必须删除向量库中的 chunks/embeddings。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="del.md", status=DocumentStatus.COMPLETED.value)
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    vector_store = _FakeVectorStore()
    chunk_repo = _FakeChunkRepo()
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )

    await service.delete_document(kb_id="kb-1", document_id="doc-1")

    # 向量库按 document_id 删除被调用
    assert vector_store.delete_calls == [("kb_1", "doc-1")]
    # PG 分块元数据也被删除
    assert chunk_repo.delete_calls == ["doc-1"]


@pytest.mark.asyncio
async def test_delete_document_vector_store_failure_does_not_block_db_delete() -> None:
    """向量库删除失败时不阻断 DB 删除（best-effort，仅记录日志）。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="del.md")
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    vector_store = _FakeVectorStore(delete_raises=True)
    chunk_repo = _FakeChunkRepo()
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )

    # 不应抛异常
    result = await service.delete_document(kb_id="kb-1", document_id="doc-1")
    assert result.id == "doc-1"
    # DB 删除仍执行
    assert doc_repo.deleted == [doc]


# ---------- 6. 重新处理已入库文件成功 ----------


@pytest.mark.asyncio
async def test_reprocess_completed_document_success() -> None:
    """用例 6：重新处理已入库文件成功（删旧向量 + 状态置 embedding + 注册后台任务）。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="re.md", status=DocumentStatus.COMPLETED.value)
    kb = _FakeKB(id="kb-1", collection_name="kb_1", embedding_dim=8)
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    vector_store = _FakeVectorStore()
    chunk_repo = _FakeChunkRepo(
        contents=[
            {"content": "chunk-0", "chunk_index": 0, "metadata": {}},
            {"content": "chunk-1", "chunk_index": 1, "metadata": {}},
        ],
    )
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        vector_store=vector_store,
        chunk_repo=chunk_repo,
    )
    bg_tasks = _RecordingBackgroundTasks()

    result = await service.reprocess_document(
        kb_id="kb-1",
        document_id="doc-1",
        background_tasks=bg_tasks,  # type: ignore[arg-type]
    )

    # 状态已置为 embedding
    assert result.status == DocumentStatus.EMBEDDING.value
    # 旧向量被删除
    assert vector_store.delete_calls == [("kb_1", "doc-1")]
    # 旧分块被删除
    assert chunk_repo.delete_calls == ["doc-1"]
    # 状态更新记录：embedding + chunk_count=0
    assert any(
        doc_id == "doc-1" and st == DocumentStatus.EMBEDDING.value for doc_id, st, _, _ in doc_repo.status_updates
    )
    # 后台任务被注册（重新 embedding + 索引）
    assert len(bg_tasks.tasks) == 1
    func, kwargs = bg_tasks.tasks[0]
    assert kwargs["document_id"] == "doc-1"
    assert kwargs["kb_id"] == "kb-1"
    assert kwargs["collection_name"] == "kb_1"
    assert len(kwargs["chunk_contents"]) == 2


@pytest.mark.asyncio
async def test_reprocess_document_without_chunks_raises() -> None:
    """重新处理但文档无分块内容（未完成分块）时拒绝并提示重新上传。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-1", name="re.md", status=DocumentStatus.FAILED.value)
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-1"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    chunk_repo = _FakeChunkRepo(contents=[])  # 无分块内容
    service = _build_service(
        doc_repo=doc_repo,
        kb_repo=kb_repo,
        chunk_repo=chunk_repo,
    )
    bg_tasks = _RecordingBackgroundTasks()

    with pytest.raises(BizException) as exc_info:
        await service.reprocess_document(
            kb_id="kb-1",
            document_id="doc-1",
            background_tasks=bg_tasks,  # type: ignore[arg-type]
        )
    # 业务错误码（非 404）
    assert exc_info.value.code == 10302
    # 后台任务未被注册
    assert len(bg_tasks.tasks) == 0


# ---------- 7. 删除不存在文件返回 404 ----------


@pytest.mark.asyncio
async def test_delete_nonexistent_document_returns_404() -> None:
    """用例 7：删除不存在的文件返回 404（code=10304）。"""
    session = _FakeSession()
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(session=session)  # 无任何文档
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.delete_document(kb_id="kb-1", document_id="nope")

    assert exc_info.value.code == 10304
    assert exc_info.value.http_status == 404


@pytest.mark.asyncio
async def test_rename_nonexistent_document_returns_404() -> None:
    """重命名不存在的文件返回 404（code=10304）。"""
    session = _FakeSession()
    kb = _FakeKB(id="kb-1")
    doc_repo = _FakeDocRepo(session=session)
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.update_document(
            kb_id="kb-1",
            document_id="nope",
            payload=DocumentUpdate(filename="x.md"),
        )
    assert exc_info.value.code == 10304
    assert exc_info.value.http_status == 404


# ---------- 8. 操作不属于当前知识库的 document 返回 404 ----------


@pytest.mark.asyncio
async def test_delete_document_not_in_kb_returns_404() -> None:
    """用例 8：document 存在但不属于当前知识库 → 404（code=10304）。"""
    session = _FakeSession()
    # doc-1 属于 kb-other，不属于 kb-1
    doc = _FakeDoc(id="doc-1", kb_id="kb-other", name="x.md")
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        # 关键：by_id_and_kb 不包含 ("doc-1", "kb-1")
        by_id_and_kb={("doc-1", "kb-other"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.delete_document(kb_id="kb-1", document_id="doc-1")

    assert exc_info.value.code == 10304
    assert exc_info.value.http_status == 404
    # 文档未被删除
    assert doc_repo.deleted == []


@pytest.mark.asyncio
async def test_rename_document_not_in_kb_returns_404() -> None:
    """重命名不属于当前知识库的 document → 404。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-other", name="x.md")
    kb = _FakeKB(id="kb-1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-other"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.update_document(
            kb_id="kb-1",
            document_id="doc-1",
            payload=DocumentUpdate(filename="new.md"),
        )
    assert exc_info.value.code == 10304
    assert exc_info.value.http_status == 404


@pytest.mark.asyncio
async def test_reprocess_document_not_in_kb_returns_404() -> None:
    """重新处理不属于当前知识库的 document → 404。"""
    session = _FakeSession()
    doc = _FakeDoc(id="doc-1", kb_id="kb-other", name="x.md")
    kb = _FakeKB(id="kb-1", collection_name="kb_1")
    doc_repo = _FakeDocRepo(
        session=session,
        by_id={"doc-1": doc},
        by_id_and_kb={("doc-1", "kb-other"): doc},
    )
    kb_repo = _FakeKBRepo(by_id={"kb-1": kb})
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)
    bg_tasks = _RecordingBackgroundTasks()

    with pytest.raises(BizException) as exc_info:
        await service.reprocess_document(
            kb_id="kb-1",
            document_id="doc-1",
            background_tasks=bg_tasks,  # type: ignore[arg-type]
        )
    assert exc_info.value.code == 10304
    assert exc_info.value.http_status == 404


# ---------- KB 不存在场景 ----------


@pytest.mark.asyncio
async def test_delete_document_kb_not_found_returns_404() -> None:
    """知识库不存在时删除文档返回 404（code=10404）。"""
    session = _FakeSession()
    doc_repo = _FakeDocRepo(session=session)
    kb_repo = _FakeKBRepo()  # 无 KB
    service = _build_service(doc_repo=doc_repo, kb_repo=kb_repo)

    with pytest.raises(BizException) as exc_info:
        await service.delete_document(kb_id="nope", document_id="doc-1")
    assert exc_info.value.code == 10404
    assert exc_info.value.http_status == 404
