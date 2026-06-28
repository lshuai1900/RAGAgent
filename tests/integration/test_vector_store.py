"""T8 Milvus 向量库集成测试。

依赖 docker-compose 启动的 Milvus。
未启动 Milvus 时通过 fixture skip。

覆盖：
- ensure_collection 幂等
- upsert 写入向量
- search 检索（按相似度排序）
- delete_by_document 按文档删除
- drop_collection
- chunk.id 作为 Milvus 主键
"""

from __future__ import annotations

import contextlib
import uuid

import pytest

from ragent.domain.dto import VectorHit, VectorRecord
from ragent.rag.vector.base import BaseVectorStore
from ragent.rag.vector.milvus import MilvusVectorStore

# 测试用 collection 前缀，便于清理
_TEST_COLLECTION_PREFIX = "test_kb_"
# 测试向量维度（小维度加速 IVF_FLAT 索引）
_TEST_DIM = 8


def _gen_collection_name() -> str:
    """生成唯一 collection 名。"""
    return f"{_TEST_COLLECTION_PREFIX}{uuid.uuid4().hex[:16]}"


def _gen_vector(seed: int, dim: int = _TEST_DIM) -> list[float]:
    """生成确定性向量（seed 决定方向）。"""
    return [float((seed + i) % 10) / 10.0 for i in range(dim)]


def _gen_record(
    record_id: str,
    seed: int,
    *,
    content: str = "",
    document_id: str = "doc-1",
    kb_id: str = "kb-1",
) -> VectorRecord:
    """构造测试向量记录。"""
    return VectorRecord(
        id=record_id,
        vector=_gen_vector(seed),
        content=content or f"content-{record_id}",
        metadata={"document_id": document_id, "kb_id": kb_id, "seed": seed},
    )


@pytest.fixture
def vector_store(milvus_available: bool) -> MilvusVectorStore:
    """提供 MilvusVectorStore 实例。"""
    return MilvusVectorStore()


@pytest.fixture
async def clean_collection(vector_store: MilvusVectorStore):
    """创建测试 collection 并在测试结束后删除。

    Yields:
        collection_name
    """
    collection_name = _gen_collection_name()
    await vector_store.ensure_collection(collection_name, _TEST_DIM)
    try:
        yield collection_name
    finally:
        with contextlib.suppress(Exception):
            await vector_store.drop_collection(collection_name)


# ---------- 协议检查 ----------


def test_milvus_vector_store_implements_base_protocol(
    milvus_available: bool,
) -> None:
    """MilvusVectorStore 符合 BaseVectorStore 协议。"""
    store = MilvusVectorStore()
    assert isinstance(store, BaseVectorStore)


# ---------- ensure_collection ----------


@pytest.mark.asyncio
async def test_ensure_collection_idempotent(
    vector_store: MilvusVectorStore,
) -> None:
    """ensure_collection 幂等：重复调用不报错。"""
    collection_name = _gen_collection_name()
    try:
        # 第一次创建
        await vector_store.ensure_collection(collection_name, _TEST_DIM)
        # 第二次：幂等，不应抛异常
        await vector_store.ensure_collection(collection_name, _TEST_DIM)
    finally:
        await vector_store.drop_collection(collection_name)


@pytest.mark.asyncio
async def test_ensure_collection_invalid_dim_raises(
    vector_store: MilvusVectorStore,
) -> None:
    """非法维度：抛 ValueError。"""
    with pytest.raises(ValueError):
        await vector_store.ensure_collection("test_invalid", 0)


# ---------- upsert ----------


@pytest.mark.asyncio
async def test_upsert_writes_vectors(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """upsert 写入向量，返回写入数量。"""
    records = [
        _gen_record("chunk-1", seed=1),
        _gen_record("chunk-2", seed=2),
        _gen_record("chunk-3", seed=3),
    ]

    count = await vector_store.upsert(clean_collection, records)

    assert count == 3


@pytest.mark.asyncio
async def test_upsert_empty_returns_zero(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """空 upsert 返回 0。"""
    count = await vector_store.upsert(clean_collection, [])
    assert count == 0


@pytest.mark.asyncio
async def test_upsert_idempotent_with_chunk_id_as_pk(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """chunk.id 作为主键：相同 id upsert 覆盖而非新增。"""
    record = _gen_record("chunk-same-id", seed=1, content="原始内容")
    await vector_store.upsert(clean_collection, [record])

    # 用相同 id 再次 upsert（覆盖）
    updated_record = _gen_record("chunk-same-id", seed=2, content="更新内容")
    await vector_store.upsert(clean_collection, [updated_record])

    # 检索应只返回一条（覆盖，不是新增）
    # 用 seed=2 的向量检索，应命中更新后的记录
    hits = await vector_store.search(clean_collection, _gen_vector(2), top_k=10)
    assert len(hits) >= 1
    # 至少有一条 id == chunk-same-id
    matched = [h for h in hits if h.id == "chunk-same-id"]
    assert len(matched) == 1
    assert matched[0].content == "更新内容"


# ---------- search ----------


@pytest.mark.asyncio
async def test_search_returns_sorted_by_similarity(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """search 返回结果按相似度从高到低排序。"""
    from tests.conftest import is_milvus_lite

    records = [
        _gen_record("chunk-a", seed=1),
        _gen_record("chunk-b", seed=5),
        _gen_record("chunk-c", seed=9),
    ]
    await vector_store.upsert(clean_collection, records)

    # 用 seed=1 的向量查询，chunk-a 应该最相似
    hits = await vector_store.search(clean_collection, _gen_vector(1), top_k=3)

    assert len(hits) >= 1
    # 相似度分数应递减（COSINE：值越大越相似）
    for i in range(len(hits) - 1):
        assert hits[i].score >= hits[i + 1].score
    # 仅在真实 Milvus（支持 COSINE 索引）下断言最相似命中
    # milvus-lite 不支持 create_index，返回 L2 距离而非 COSINE 相似度
    if not is_milvus_lite():
        assert hits[0].id == "chunk-a"


@pytest.mark.asyncio
async def test_search_with_filter_expr(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """search 支持过滤表达式（按 document_id 过滤）。"""
    records = [
        _gen_record("chunk-d1", seed=1, document_id="doc-A"),
        _gen_record("chunk-d2", seed=2, document_id="doc-A"),
        _gen_record("chunk-d3", seed=3, document_id="doc-B"),
    ]
    await vector_store.upsert(clean_collection, records)

    # 仅检索 doc-A 的向量
    hits = await vector_store.search(
        clean_collection,
        _gen_vector(1),
        top_k=10,
        filter_expr='document_id == "doc-A"',
    )

    assert len(hits) >= 1
    for hit in hits:
        assert hit.metadata.get("document_id") == "doc-A"


@pytest.mark.asyncio
async def test_search_top_k_zero_returns_empty(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """top_k=0 返回空列表。"""
    await vector_store.upsert(clean_collection, [_gen_record("c1", 1)])
    hits = await vector_store.search(clean_collection, _gen_vector(1), top_k=0)
    assert hits == []


# ---------- delete_by_document ----------


@pytest.mark.asyncio
async def test_delete_by_document_removes_vectors(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """delete_by_document 删除指定文档的所有向量。"""
    records = [
        _gen_record("del-1", seed=1, document_id="doc-del"),
        _gen_record("del-2", seed=2, document_id="doc-del"),
        _gen_record("keep-1", seed=3, document_id="doc-keep"),
    ]
    await vector_store.upsert(clean_collection, records)

    # 删除 doc-del 的所有向量
    await vector_store.delete_by_document(clean_collection, "doc-del")

    # 检索应只剩 doc-keep 的向量
    hits = await vector_store.search(clean_collection, _gen_vector(1), top_k=10)
    for hit in hits:
        assert hit.metadata.get("document_id") != "doc-del"


# ---------- drop_collection ----------


@pytest.mark.asyncio
async def test_drop_collection(vector_store: MilvusVectorStore) -> None:
    """drop_collection 删除 collection。"""
    collection_name = _gen_collection_name()
    await vector_store.ensure_collection(collection_name, _TEST_DIM)
    await vector_store.drop_collection(collection_name)

    # 再次 ensure 应能成功（已删除，重新创建）
    await vector_store.ensure_collection(collection_name, _TEST_DIM)
    # 清理
    await vector_store.drop_collection(collection_name)


# ---------- VectorHit 结构验证 ----------


@pytest.mark.asyncio
async def test_search_returns_vector_hit_instances(
    vector_store: MilvusVectorStore,
    clean_collection: str,
) -> None:
    """search 返回 VectorHit 实例。"""
    await vector_store.upsert(clean_collection, [_gen_record("vh-1", 1)])
    hits = await vector_store.search(clean_collection, _gen_vector(1), top_k=1)

    assert len(hits) >= 1
    hit = hits[0]
    assert isinstance(hit, VectorHit)
    assert hit.id == "vh-1"
    assert isinstance(hit.score, float)
    assert isinstance(hit.content, str)
    assert isinstance(hit.metadata, dict)
