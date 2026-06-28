"""T10 检索器与后处理单元测试。

约束：
- 不依赖真实 Milvus / Embedding / DB，全部 Mock
- 覆盖：
  - VectorRetriever 正常检索（embed → search → map）
  - kb_id 缺失抛 BizException
  - KB 不存在抛 BizException
  - 空查询返回空列表
  - top_k <= 0 返回空列表
  - channel_name 正确
  - DeduplicationPostProcessor 按 chunk_id 去重保留最高分
  - DeduplicationPostProcessor 保留首次出现顺序
  - IdentityReranker 直通截断
"""

from __future__ import annotations

from typing import Any

import pytest

from ragent.domain.dto import RetrievalResult, VectorHit
from ragent.domain.value_objects import RetrievalQuery
from ragent.framework.core.exceptions import BizException
from ragent.infra_ai.rerank.base import BaseReranker
from ragent.infra_ai.rerank.identity import IdentityReranker
from ragent.rag.retrieve.base import BaseRetriever
from ragent.rag.retrieve.postprocessor.base import BasePostProcessor
from ragent.rag.retrieve.postprocessor.dedup import DeduplicationPostProcessor
from ragent.rag.retrieve.vector_retriever import VectorRetriever

# ---------- Mock 依赖 ----------


class _MockEmbeddingClient:
    """Mock Embedding 客户端：返回确定性向量。"""

    async def embed_one(self, text: str) -> list[float]:
        # 简单确定性向量
        return [float(len(text)), float(sum(ord(c) for c in text) % 100)]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_one(t) for t in texts]

    def dim(self) -> int:
        return 2

    def model_name(self) -> str:
        return "mock-embedding"


class _MockVectorStore:
    """Mock VectorStore：按预设 hits 返回。"""

    def __init__(self, hits: list[VectorHit]) -> None:
        self._hits = hits
        self.last_search_args: dict[str, Any] | None = None

    async def search(
        self,
        *,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filter_expr: str | None = None,
    ) -> list[VectorHit]:
        self.last_search_args = {
            "collection_name": collection_name,
            "query_vector": query_vector,
            "top_k": top_k,
            "filter_expr": filter_expr,
        }
        return list(self._hits[:top_k])


class _MockKbEntity:
    """Mock KB 实体（仅需 collection_name 字段）。"""

    def __init__(self, collection_name: str, embedding_dim: int = 2) -> None:
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim


class _MockKbRepo:
    """Mock KnowledgeBaseRepository。"""

    def __init__(self, kb: _MockKbEntity | None) -> None:
        self._kb = kb
        self.last_get_id: str | None = None

    async def get_by_id(self, id: str) -> _MockKbEntity | None:
        self.last_get_id = id
        return self._kb


def _make_hit(hit_id: str, score: float, content: str, document_id: str) -> VectorHit:
    """构造 VectorHit。"""
    return VectorHit(
        id=hit_id,
        score=score,
        content=content,
        metadata={"document_id": document_id, "kb_id": "kb-1"},
    )


# ---------- VectorRetriever 协议与基本属性 ----------


def test_vector_retriever_implements_base_protocol() -> None:
    """VectorRetriever 符合 BaseRetriever 协议。"""
    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=_MockVectorStore([]),
        kb_repo=_MockKbRepo(_MockKbEntity("kb_test")),
    )
    assert isinstance(retriever, BaseRetriever)
    assert retriever.channel_name() == "vector_default"


# ---------- VectorRetriever 正常检索 ----------


@pytest.mark.asyncio
async def test_vector_retriever_normal() -> None:
    """正常检索：embed → search → map to RetrievalResult。"""
    hits = [
        _make_hit("chunk-1", 0.9, "内容1", "doc-1"),
        _make_hit("chunk-2", 0.8, "内容2", "doc-1"),
    ]
    vector_store = _MockVectorStore(hits)
    kb_repo = _MockKbRepo(_MockKbEntity("kb_test_collection"))

    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=vector_store,
        kb_repo=kb_repo,
    )

    query = RetrievalQuery(text="查询", kb_id="kb-1")
    results = await retriever.retrieve(query, top_k=5)

    assert len(results) == 2
    assert all(isinstance(r, RetrievalResult) for r in results)
    assert results[0].chunk_id == "chunk-1"
    assert results[0].score == 0.9
    assert results[0].content == "内容1"
    assert results[0].document_id == "doc-1"
    assert results[0].kb_id == "kb-1"
    assert results[0].retrieval_channel == "vector_default"
    assert results[0].rerank_score is None

    # 验证 kb_repo 被正确调用
    assert kb_repo.last_get_id == "kb-1"
    # 验证 collection_name 来自 KB
    assert vector_store.last_search_args is not None
    assert vector_store.last_search_args["collection_name"] == "kb_test_collection"
    # 验证 filter_expr 含 kb_id
    assert 'kb_id == "kb-1"' in (vector_store.last_search_args["filter_expr"] or "")


@pytest.mark.asyncio
async def test_vector_retriever_filter_by_kb_id() -> None:
    """检索时按 kb_id 过滤。"""
    vector_store = _MockVectorStore([])
    kb_repo = _MockKbRepo(_MockKbEntity("coll_x"))

    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=vector_store,
        kb_repo=kb_repo,
    )

    query = RetrievalQuery(text="q", kb_id="my-kb-id")
    await retriever.retrieve(query, top_k=3)

    assert vector_store.last_search_args is not None
    assert 'kb_id == "my-kb-id"' in (vector_store.last_search_args["filter_expr"] or "")


@pytest.mark.asyncio
async def test_vector_retriever_top_k_passed_through() -> None:
    """top_k 透传到 vector_store.search。"""
    vector_store = _MockVectorStore([])
    kb_repo = _MockKbRepo(_MockKbEntity("c"))

    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=vector_store,
        kb_repo=kb_repo,
    )

    await retriever.retrieve(RetrievalQuery(text="q", kb_id="k"), top_k=7)
    assert vector_store.last_search_args is not None
    assert vector_store.last_search_args["top_k"] == 7


# ---------- VectorRetriever 错误路径 ----------


@pytest.mark.asyncio
async def test_vector_retriever_missing_kb_id_raises() -> None:
    """kb_id 缺失：抛 BizException(10401)。"""
    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=_MockVectorStore([]),
        kb_repo=_MockKbRepo(None),
    )

    query = RetrievalQuery(text="q", kb_id=None)
    with pytest.raises(BizException) as exc_info:
        await retriever.retrieve(query, top_k=5)
    assert exc_info.value.code == 10401


@pytest.mark.asyncio
async def test_vector_retriever_kb_not_found_raises() -> None:
    """KB 不存在：抛 BizException(10404)。"""
    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=_MockVectorStore([]),
        kb_repo=_MockKbRepo(None),  # 返回 None 表示不存在
    )

    query = RetrievalQuery(text="q", kb_id="non-existent")
    with pytest.raises(BizException) as exc_info:
        await retriever.retrieve(query, top_k=5)
    assert exc_info.value.code == 10404


@pytest.mark.asyncio
async def test_vector_retriever_empty_query_returns_empty() -> None:
    """空查询返回空列表，不调用检索。"""
    vector_store = _MockVectorStore([])
    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=vector_store,
        kb_repo=_MockKbRepo(_MockKbEntity("c")),
    )

    results = await retriever.retrieve(RetrievalQuery(text="", kb_id="k"), top_k=5)
    assert results == []
    # 未触发 search
    assert vector_store.last_search_args is None


@pytest.mark.asyncio
async def test_vector_retriever_top_k_le_zero_returns_empty() -> None:
    """top_k <= 0 返回空列表。"""
    retriever = VectorRetriever(
        embedding_client=_MockEmbeddingClient(),
        vector_store=_MockVectorStore([_make_hit("c1", 0.5, "x", "d")]),
        kb_repo=_MockKbRepo(_MockKbEntity("c")),
    )

    results = await retriever.retrieve(RetrievalQuery(text="q", kb_id="k"), top_k=0)
    assert results == []


# ---------- DeduplicationPostProcessor ----------


def test_dedup_implements_base_protocol() -> None:
    """DeduplicationPostProcessor 符合 BasePostProcessor 协议。"""
    p = DeduplicationPostProcessor()
    assert isinstance(p, BasePostProcessor)
    assert p.order() == 1


@pytest.mark.asyncio
async def test_dedup_keeps_highest_score() -> None:
    """同 chunk_id 出现多次时，保留 score 最高的那条。"""
    p = DeduplicationPostProcessor()
    results = [
        RetrievalResult(chunk_id="c1", document_id="d1", kb_id="k", content="A", score=0.7),
        RetrievalResult(chunk_id="c1", document_id="d1", kb_id="k", content="A", score=0.9),
        RetrievalResult(chunk_id="c1", document_id="d1", kb_id="k", content="A", score=0.5),
    ]
    out = await p.process("query", results)
    assert len(out) == 1
    assert out[0].score == 0.9


@pytest.mark.asyncio
async def test_dedup_preserves_first_occurrence_order() -> None:
    """去重后保持首次出现的相对顺序。"""
    p = DeduplicationPostProcessor()
    results = [
        RetrievalResult(chunk_id="c2", document_id="d", kb_id="k", content="B", score=0.8),
        RetrievalResult(chunk_id="c1", document_id="d", kb_id="k", content="A", score=0.9),
        RetrievalResult(chunk_id="c2", document_id="d", kb_id="k", content="B", score=0.95),  # 重复
        RetrievalResult(chunk_id="c3", document_id="d", kb_id="k", content="C", score=0.6),
    ]
    out = await p.process("q", results)
    assert [r.chunk_id for r in out] == ["c2", "c1", "c3"]
    # c2 保留最高分 0.95
    assert out[0].score == 0.95
    assert out[1].score == 0.9
    assert out[2].score == 0.6


@pytest.mark.asyncio
async def test_dedup_empty_input() -> None:
    """空输入返回空列表。"""
    p = DeduplicationPostProcessor()
    out = await p.process("q", [])
    assert out == []


@pytest.mark.asyncio
async def test_dedup_no_duplicates_unchanged() -> None:
    """无重复时，输出与输入一致。"""
    p = DeduplicationPostProcessor()
    results = [
        RetrievalResult(chunk_id="c1", document_id="d", kb_id="k", content="A", score=0.9),
        RetrievalResult(chunk_id="c2", document_id="d", kb_id="k", content="B", score=0.8),
    ]
    out = await p.process("q", results)
    assert len(out) == 2
    assert [r.chunk_id for r in out] == ["c1", "c2"]


# ---------- IdentityReranker ----------


def test_identity_reranker_implements_base_protocol() -> None:
    """IdentityReranker 符合 BaseReranker 协议。"""
    r = IdentityReranker()
    assert isinstance(r, BaseReranker)
    assert r.enabled() is True


@pytest.mark.asyncio
async def test_identity_reranker_truncates_to_top_k() -> None:
    """直通截断到 top_k，不改变顺序。"""
    r = IdentityReranker()
    candidates = [
        RetrievalResult(chunk_id=f"c{i}", document_id="d", kb_id="k", content=f"x{i}", score=0.1 * i) for i in range(5)
    ]
    out = await r.rerank("q", candidates, top_k=3)
    assert len(out) == 3
    # 顺序不变
    assert [r.chunk_id for r in out] == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_identity_reranker_top_k_larger_than_candidates() -> None:
    """top_k 大于候选数时返回全部。"""
    r = IdentityReranker()
    candidates = [
        RetrievalResult(chunk_id="c1", document_id="d", kb_id="k", content="x", score=0.9),
    ]
    out = await r.rerank("q", candidates, top_k=10)
    assert len(out) == 1


@pytest.mark.asyncio
async def test_identity_reranker_top_k_zero() -> None:
    """top_k <= 0 返回空列表。"""
    r = IdentityReranker()
    candidates = [
        RetrievalResult(chunk_id="c1", document_id="d", kb_id="k", content="x", score=0.9),
    ]
    out = await r.rerank("q", candidates, top_k=0)
    assert out == []
