"""T9 摄取 Pipeline 集成测试。

依赖 docker-compose 启动的 PostgreSQL + Milvus。
Embedding 客户端用 Mock（避免真实调用外部模型）。

覆盖：
- Pipeline 端到端：parse → chunk → embed → index
- Chunk 元数据写入 PostgreSQL
- 向量写入 Milvus
- chunk.id 与 Milvus 主键一致
- DocumentChunk 状态机更新
"""

from __future__ import annotations

import contextlib
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ragent.domain.dto import ChunkDraft, ParsedDocument
from ragent.domain.enums import ChunkEmbeddingStatus
from ragent.framework.core.snowflake import generate_id
from ragent.framework.db.session import (
    dispose_engine,
    get_engine,
    get_session_factory,
)
from ragent.ingestion.chunker.recursive import RecursiveChunker
from ragent.ingestion.parser.txt import TxtParser
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.persistence.models.document import Document
from ragent.persistence.models.knowledge_base import KnowledgeBase
from ragent.persistence.repositories.chunk_repo import DocumentChunkRepository
from ragent.rag.vector.milvus import MilvusVectorStore

# 测试用维度
_TEST_DIM = 8
_TEST_COLLECTION_PREFIX = "test_pipeline_"


# ---------- Mock Embedding Client ----------


class MockEmbeddingClient:
    """Mock Embedding 客户端：返回确定性向量，避免真实调用。"""

    def __init__(self, dim: int = _TEST_DIM) -> None:
        self._dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._make_vector(t) for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return self._make_vector(text)

    def dim(self) -> int:
        return self._dim

    def model_name(self) -> str:
        return "mock-embedding"

    def _make_vector(self, text: str) -> list[float]:
        """根据文本 hash 生成确定性向量。"""
        h = abs(hash(text)) % 100
        return [float((h + i) % 10) / 10.0 for i in range(self._dim)]


# ---------- Fixtures ----------


@pytest.fixture
async def db_session(
    postgres_available: bool,
) -> AsyncSession:
    """提供 PostgreSQL AsyncSession，确保表结构已迁移。"""
    # 重置 engine 单例，避免上一轮测试遗留
    await dispose_engine()

    engine = get_engine()
    # 确保表已创建（alembic 已迁移）
    async with engine.begin() as conn:
        # 仅检查表是否存在，不重复创建（依赖 alembic upgrade head）
        result = await conn.execute(text("SELECT to_regclass('t_document_chunk')"))
        if result.scalar() is None:
            pytest.skip("数据库表未迁移，请先执行 alembic upgrade head")

    factory = get_session_factory()
    async with factory() as session:
        yield session

    await dispose_engine()


@pytest.fixture
async def clean_kb_and_collection(db_session: AsyncSession):
    """创建测试 KB + Document + Milvus collection，测试结束清理。

    Yields:
        (kb, document, collection_name)
    """
    vector_store = MilvusVectorStore()
    collection_name = f"{_TEST_COLLECTION_PREFIX}{uuid.uuid4().hex[:16]}"

    # 创建 collection
    await vector_store.ensure_collection(collection_name, _TEST_DIM)

    # 创建测试 KB
    kb_id = generate_id()
    kb = KnowledgeBase(
        id=kb_id,
        name=f"test-kb-{kb_id[:8]}",
        description="测试知识库",
        collection_name=collection_name,
        embedding_dim=_TEST_DIM,
        embedding_model="mock-embedding",
        chunk_strategy="recursive",
        chunk_size=100,
        chunk_overlap=10,
        document_count=1,
        status="active",
    )
    db_session.add(kb)
    # 先 flush KB，确保 FK 约束在 Document 插入时满足
    await db_session.flush()

    # 创建测试 Document
    doc_id = generate_id()
    document = Document(
        id=doc_id,
        kb_id=kb_id,
        name="test.txt",
        file_type="txt",
        file_size=100,
        file_hash=f"test-hash-{uuid.uuid4().hex}",
        status="pending",
        chunk_count=0,
        total_tokens=0,
    )
    db_session.add(document)
    await db_session.commit()

    try:
        yield kb, document, collection_name, vector_store
    finally:
        # 清理 Milvus
        with contextlib.suppress(Exception):
            await vector_store.drop_collection(collection_name)
        # 清理 PostgreSQL
        await db_session.execute(
            text("DELETE FROM t_document_chunk WHERE kb_id = :kb_id"),
            {"kb_id": kb_id},
        )
        await db_session.execute(
            text("DELETE FROM t_document WHERE kb_id = :kb_id"),
            {"kb_id": kb_id},
        )
        await db_session.execute(
            text("DELETE FROM t_knowledge_base WHERE id = :kb_id"),
            {"kb_id": kb_id},
        )
        await db_session.commit()


# ---------- Pipeline 端到端 ----------


@pytest.mark.asyncio
async def test_pipeline_run_end_to_end(
    db_session: AsyncSession,
    clean_kb_and_collection: Any,
    tmp_path: Path,
) -> None:
    """Pipeline 端到端：parse → chunk → embed → index。

    验证：
    - PostgreSQL 写入 chunk 元数据
    - Milvus 写入向量
    - chunk.id 与 Milvus 主键一致
    - DocumentChunk 状态更新为 indexed
    """
    kb, document, collection_name, vector_store = clean_kb_and_collection

    # 准备测试文件
    file_path = tmp_path / "test.txt"
    file_path.write_text(
        "这是第一段内容，用于测试 pipeline。这是第二段内容，更长一些，确保会被切分为多个分块。" * 10,
        encoding="utf-8",
    )

    # 构造 Pipeline（Mock Embedding + Real Milvus）
    pipeline = IngestionPipeline(
        parser=TxtParser(),
        chunker=RecursiveChunker(),
        embedding_client=MockEmbeddingClient(dim=_TEST_DIM),
        vector_store=vector_store,
    )

    chunk_repo = DocumentChunkRepository(db_session)

    # 运行 pipeline
    indexed_count = await pipeline.run(
        file_path=file_path,
        file_type="txt",
        document_id=document.id,
        kb_id=kb.id,
        collection_name=collection_name,
        chunk_size=80,
        chunk_overlap=10,
        chunk_repo=chunk_repo,
    )
    await db_session.commit()

    # 验证：PostgreSQL 写入 chunk 元数据
    assert indexed_count > 0
    chunks_in_db = await chunk_repo.list_by_document(document.id)
    assert len(chunks_in_db) == indexed_count
    for chunk in chunks_in_db:
        assert chunk.embedding_status == ChunkEmbeddingStatus.INDEXED.value
        assert chunk.document_id == document.id
        assert chunk.kb_id == kb.id
        assert len(chunk.content) > 0

    # 验证：Milvus 写入向量（按 document_id 过滤检索）
    # 用 chunk 0 的向量作为查询向量（应能命中自身）
    query_vector = MockEmbeddingClient(_TEST_DIM)._make_vector(chunks_in_db[0].content)
    hits = await vector_store.search(
        collection_name,
        query_vector,
        top_k=100,
        filter_expr=f'document_id == "{document.id}"',
    )

    assert len(hits) == indexed_count
    # 验证：chunk.id 与 Milvus 主键一致
    chunk_ids_in_db = {c.id for c in chunks_in_db}
    chunk_ids_in_milvus = {h.id for h in hits}
    assert chunk_ids_in_db == chunk_ids_in_milvus


@pytest.mark.asyncio
async def test_pipeline_index_writes_metadata_and_vectors(
    db_session: AsyncSession,
    clean_kb_and_collection: Any,
) -> None:
    """Pipeline index 阶段：同时写 PostgreSQL 元数据与 Milvus 向量。"""
    kb, document, collection_name, vector_store = clean_kb_and_collection

    # 构造 ChunkDraft（跳过 parse/chunk/embed 阶段）
    chunks = [
        ChunkDraft(content="测试 chunk 1", chunk_index=0, metadata={"page": 1}),
        ChunkDraft(content="测试 chunk 2", chunk_index=1, metadata={"page": 2}),
    ]
    mock_embedding = MockEmbeddingClient(dim=_TEST_DIM)
    vectors = [await mock_embedding.embed_one(c.content) for c in chunks]

    pipeline = IngestionPipeline(
        embedding_client=mock_embedding,
        vector_store=vector_store,
    )
    chunk_repo = DocumentChunkRepository(db_session)

    indexed = await pipeline.index(
        collection_name,
        chunks,
        vectors,
        document_id=document.id,
        kb_id=kb.id,
        chunk_repo=chunk_repo,
    )
    await db_session.commit()

    assert indexed == 2

    # 验证 PostgreSQL
    chunks_in_db = await chunk_repo.list_by_document(document.id)
    assert len(chunks_in_db) == 2
    assert chunks_in_db[0].chunk_index == 0
    assert chunks_in_db[1].chunk_index == 1
    # metadata 包含 document_id / kb_id（pipeline 注入）
    assert chunks_in_db[0].chunk_metadata["document_id"] == document.id
    assert chunks_in_db[0].chunk_metadata["kb_id"] == kb.id

    # 验证 Milvus
    hits = await vector_store.search(
        collection_name,
        vectors[0],
        top_k=10,
        filter_expr=f'document_id == "{document.id}"',
    )
    assert len(hits) == 2


@pytest.mark.asyncio
async def test_pipeline_empty_chunks_returns_zero(
    db_session: AsyncSession,
    clean_kb_and_collection: Any,
) -> None:
    """Pipeline 空分块：index 返回 0，不写任何数据。"""
    _kb, _document, collection_name, vector_store = clean_kb_and_collection

    pipeline = IngestionPipeline(
        embedding_client=MockEmbeddingClient(dim=_TEST_DIM),
        vector_store=vector_store,
    )
    chunk_repo = DocumentChunkRepository(db_session)

    indexed = await pipeline.index(
        collection_name,
        [],
        [],
        document_id="non-existent-doc",
        kb_id="non-existent-kb",
        chunk_repo=chunk_repo,
    )

    assert indexed == 0


@pytest.mark.asyncio
async def test_pipeline_chunk_and_embed_stages(
    db_session: AsyncSession,
    clean_kb_and_collection: Any,
    tmp_path: Path,
) -> None:
    """Pipeline chunk + embed 阶段独立调用。"""
    _kb, _document, _collection_name, vector_store = clean_kb_and_collection

    file_path = tmp_path / "demo.txt"
    file_path.write_text("测试文本一。测试文本二。测试文本三。" * 5, encoding="utf-8")

    pipeline = IngestionPipeline(
        parser=TxtParser(),
        chunker=RecursiveChunker(),
        embedding_client=MockEmbeddingClient(dim=_TEST_DIM),
        vector_store=vector_store,
    )

    # parse
    parsed = await pipeline.parse(file_path, "txt")
    assert isinstance(parsed, ParsedDocument)
    assert len(parsed.text) > 0

    # chunk
    chunks = await pipeline.chunk(parsed, chunk_size=30, chunk_overlap=5)
    assert len(chunks) >= 1
    assert all(isinstance(c, ChunkDraft) for c in chunks)
    _assert_chunk_indices_sequential(chunks)

    # embed
    vectors = await pipeline.embed(chunks)
    assert len(vectors) == len(chunks)
    for v in vectors:
        assert len(v) == _TEST_DIM


@pytest.mark.asyncio
async def test_pipeline_embed_empty_returns_empty(
    db_session: AsyncSession,
    clean_kb_and_collection: Any,
) -> None:
    """Pipeline embed 空分块：返回空向量列表。"""
    _kb, _document, _collection_name, vector_store = clean_kb_and_collection

    pipeline = IngestionPipeline(
        embedding_client=MockEmbeddingClient(dim=_TEST_DIM),
        vector_store=vector_store,
    )

    vectors = await pipeline.embed([])
    assert vectors == []


# ---------- 辅助函数 ----------


def _assert_chunk_indices_sequential(chunks: list[ChunkDraft]) -> None:
    """chunk_index 从 0 开始递增。"""
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i
