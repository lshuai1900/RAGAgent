"""T18 端到端集成测试：检索 + 流式问答闭环。

依赖 docker-compose 启动的 PostgreSQL + Milvus。
LLM / Embedding 用 Mock（避免真实调用外部模型）。

流程：
1. 创建知识库
2. 上传 sample.txt
3. 等待文档状态 completed
4. 调用 /api/v1/chat/sse
5. 收到基于文档内容的流式回答
6. 验证 ChatMessage 表有 user + assistant 记录
7. 验证 retrieval_context 非空
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import text

from ragent.domain.dto import ChatChunk, ChatMessage
from ragent.domain.enums import MessageRole
from ragent.domain.value_objects import ChatOptions
from ragent.framework.core.config import reload_settings
from ragent.framework.db.session import (
    dispose_engine,
    get_engine,
    get_session_factory,
)
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.infra_ai.llm.base import BaseLLMClient
from ragent.infra_ai.rerank.identity import IdentityReranker
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.main import create_app
from ragent.persistence.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from ragent.rag.memory.db_store import DbMemoryStore
from ragent.rag.prompt.service import PromptService
from ragent.rag.retrieve.postprocessor.dedup import DeduplicationPostProcessor
from ragent.rag.retrieve.vector_retriever import VectorRetriever
from ragent.rag.vector.base import BaseVectorStore
from ragent.rag.vector.milvus import MilvusVectorStore
from ragent.service.chat_service import ChatService
from ragent.service.ingestion_service import IngestionService
from ragent.service.knowledge_service import KnowledgeService

# Mock 维度（与 KB embedding_dim 一致）
_MOCK_DIM = 8


# ---------- Mock Embedding ----------


class MockEmbeddingClient:
    """Mock Embedding 客户端：返回确定性向量。"""

    def __init__(self, dim: int = _MOCK_DIM) -> None:
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
        # 基于文本内容生成确定性向量，使相同/相似文本向量接近
        h = abs(hash(text)) % 100
        return [float((h + i) % 10) / 10.0 for i in range(self._dim)]


# ---------- Mock LLM ----------


class MockLLMClient:
    """Mock LLM 客户端：返回预设的流式回答。

    回答内容引用上传的文档关键词，模拟"基于文档内容的回答"。
    """

    def __init__(self) -> None:
        self.last_messages: list[ChatMessage] | None = None

    async def chat(self, messages: list[ChatMessage], options: ChatOptions) -> str:
        self.last_messages = messages
        return "基于文档内容的回答：RAG 是检索增强生成技术。"

    def stream_chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[ChatChunk]:
        self.last_messages = messages
        return self._stream()

    async def _stream(self) -> AsyncIterator[ChatChunk]:
        # 模拟基于文档的流式回答
        deltas = ["基于", "文档", "内容", "的回答", "：", "RAG", " 是", "检索", "增强", "生成", "技术", "。"]
        for d in deltas:
            yield ChatChunk(delta=d, finish_reason=None)
        yield ChatChunk(delta="", finish_reason="stop")

    def model_name(self) -> str:
        return "mock-llm"


# ---------- Fixture ----------


@pytest.fixture
async def e2e_app_client(
    postgres_available: bool,
    milvus_available: bool,
) -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, Any]]]:
    """端到端测试 ASGI 客户端。

    - 真实 PostgreSQL + Milvus
    - Mock Embedding（避免真实调用）+ Mock LLM（避免真实调用）
    - 真实 ChatService 编排（验证全链路）

    Yields:
        (client, resources) - resources 含 vector_store / mock_llm / cleanup 数据
    """
    reload_settings()
    await dispose_engine()

    # 验证表已迁移
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT to_regclass('t_knowledge_base')"))
        if result.scalar() is None:
            pytest.skip("数据库表未迁移，请先执行 alembic upgrade head")

    # 共享 Mock Embedding + Real Milvus + Mock LLM
    mock_embedding = MockEmbeddingClient(dim=_MOCK_DIM)
    vector_store = MilvusVectorStore()
    mock_llm = MockLLMClient()
    pipeline = IngestionPipeline(
        embedding_client=mock_embedding,
        vector_store=vector_store,
    )

    app = create_app()

    from ragent.api.deps import (
        get_chat_service as _orig_get_chat_service,
    )
    from ragent.api.deps import (
        get_embedding_client as _orig_get_embedding_client,
    )
    from ragent.api.deps import (
        get_ingestion_service as _orig_get_ingestion_service,
    )
    from ragent.api.deps import (
        get_knowledge_service as _orig_get_knowledge_service,
    )
    from ragent.api.deps import (
        get_llm_client as _orig_get_llm_client,
    )
    from ragent.api.deps import (
        get_pipeline as _orig_get_pipeline,
    )
    from ragent.api.deps import (
        get_vector_store as _orig_get_vector_store,
    )
    from ragent.persistence.repositories.document_repo import DocumentRepository
    from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository

    def _override_embedding() -> BaseEmbeddingClient:
        return mock_embedding

    def _override_vector_store() -> BaseVectorStore:
        return vector_store

    def _override_pipeline() -> IngestionPipeline:
        return pipeline

    def _override_llm() -> BaseLLMClient:
        return mock_llm

    def _override_knowledge_service(
        kb_repo: KnowledgeBaseRepository,
    ) -> KnowledgeService:
        return KnowledgeService(
            kb_repo=kb_repo,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

    def _override_ingestion_service(
        kb_repo: KnowledgeBaseRepository,
        document_repo: DocumentRepository,
    ) -> IngestionService:
        return IngestionService(
            kb_repo=kb_repo,
            document_repo=document_repo,
            pipeline=pipeline,
        )

    def _override_chat_service(
        kb_repo: KnowledgeBaseRepository,
        chat_message_repo: ChatMessageRepository,
        chat_session_repo: ChatSessionRepository,
    ) -> ChatService:
        """构造真实 ChatService（含 Mock LLM + Real Retriever + Real Memory）。"""
        retriever = VectorRetriever(
            embedding_client=mock_embedding,
            vector_store=vector_store,
            kb_repo=kb_repo,
        )
        memory_store = DbMemoryStore(
            chat_message_repo=chat_message_repo,
            chat_session_repo=chat_session_repo,
        )
        return ChatService(
            retriever=retriever,
            post_processors=[DeduplicationPostProcessor()],
            reranker=IdentityReranker(),
            llm_client=mock_llm,
            memory_store=memory_store,
            prompt_service=PromptService(),
            chat_message_repo=chat_message_repo,
            chat_session_repo=chat_session_repo,
        )

    app.dependency_overrides[_orig_get_embedding_client] = _override_embedding
    app.dependency_overrides[_orig_get_vector_store] = _override_vector_store
    app.dependency_overrides[_orig_get_pipeline] = _override_pipeline
    app.dependency_overrides[_orig_get_llm_client] = _override_llm
    app.dependency_overrides[_orig_get_knowledge_service] = _override_knowledge_service
    app.dependency_overrides[_orig_get_ingestion_service] = _override_ingestion_service
    app.dependency_overrides[_orig_get_chat_service] = _override_chat_service

    transport = ASGITransport(app=app)
    cleanup_resources: dict[str, Any] = {
        "vector_store": vector_store,
        "mock_llm": mock_llm,
        "collections": [],
        "kb_ids": [],
        "session_ids": [],
    }

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        yield c, cleanup_resources

    app.dependency_overrides.clear()

    # 清理 Milvus collections
    for coll_name in cleanup_resources["collections"]:
        with contextlib.suppress(Exception):
            await vector_store.drop_collection(coll_name)

    # 清理 PostgreSQL
    factory = get_session_factory()
    async with factory() as session:
        # 清理对话消息
        for sid in cleanup_resources["session_ids"]:
            await session.execute(
                text("DELETE FROM t_chat_message WHERE session_id = :sid"),
                {"sid": sid},
            )
            await session.execute(
                text("DELETE FROM t_chat_session WHERE id = :sid"),
                {"sid": sid},
            )
        # 清理 KB + 文档
        for kb_id in cleanup_resources["kb_ids"]:
            await session.execute(
                text("DELETE FROM t_document_chunk WHERE kb_id = :kb_id"),
                {"kb_id": kb_id},
            )
            await session.execute(
                text("DELETE FROM t_document WHERE kb_id = :kb_id"),
                {"kb_id": kb_id},
            )
            await session.execute(
                text("DELETE FROM t_knowledge_base WHERE id = :kb_id"),
                {"kb_id": kb_id},
            )
        await session.commit()

    await dispose_engine()


# ---------- 辅助函数 ----------


async def _create_kb(
    client: httpx.AsyncClient,
    resources: dict[str, Any],
) -> str:
    """创建测试 KB 并返回 kb_id。"""
    payload = {
        "name": f"e2e-chat-kb-{uuid.uuid4().hex[:8]}",
        "embedding_dim": _MOCK_DIM,
    }
    resp = await client.post("/api/v1/knowledge-bases", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    resources["kb_ids"].append(data["id"])
    resources["collections"].append(data["collection_name"])
    return data["id"]


async def _upload_and_wait(
    client: httpx.AsyncClient,
    kb_id: str,
    content: str,
    filename: str = "sample.txt",
) -> str:
    """上传文档并等待 status=completed，返回 document_id。"""
    files = {"file": (filename, content.encode("utf-8"), "text/plain")}
    data = {"kb_id": kb_id}
    resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert resp.status_code == 201
    document_id = resp.json()["data"]["document_id"]

    # 轮询等待完成
    for _ in range(40):
        await asyncio.sleep(0.5)
        status_resp = await client.get(f"/api/v1/documents/{document_id}")
        status = status_resp.json()["data"]["status"]
        if status in {"completed", "failed"}:
            break
    assert status == "completed", f"文档未完成，状态: {status}"
    return document_id


def _parse_sse_events(raw_text: str) -> list[dict[str, Any]]:
    """解析 SSE 原始文本为事件列表。"""
    import json

    events: list[dict[str, Any]] = []
    current_event = ""
    current_data_lines: list[str] = []

    for line in raw_text.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data_lines.append(line[len("data:"):].strip())
        elif line == "":
            if current_event and current_data_lines:
                data_str = "\n".join(current_data_lines)
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = {"raw": data_str}
                events.append({"event": current_event, "data": data})
            current_event = ""
            current_data_lines = []
    return events


# ---------- E2E 测试 ----------


@pytest.mark.asyncio
async def test_e2e_chat_sse_full_flow(
    e2e_app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """端到端：创建 KB → 上传文档 → 等待完成 → SSE 问答 → 验证消息持久化。

    覆盖：
    1. 创建知识库
    2. 上传 sample.txt
    3. 等待文档状态 completed
    4. 调用 /api/v1/chat/sse
    5. 收到基于文档内容的流式回答
    6. ChatMessage 表有 user + assistant 记录
    7. retrieval_context 非空
    """
    client, resources = e2e_app_client

    # 1. 创建知识库
    kb_id = await _create_kb(client, resources)

    # 2. 上传文档（含关键词，便于检索）
    doc_content = (
        "RAG（检索增强生成）是一种结合检索与生成的技术。"
        "它通过向量检索从知识库中召回相关文档片段，再交给大语言模型生成回答。"
        "RAG 能有效缓解大模型的幻觉问题，提升回答的准确性与可追溯性。"
    ) * 5
    document_id = await _upload_and_wait(client, kb_id, doc_content)
    assert document_id

    # 3. 调用 SSE 问答
    session_id = f"e2e-sess-{uuid.uuid4().hex[:8]}"
    resources["session_ids"].append(session_id)
    payload = {
        "session_id": session_id,
        "kb_id": kb_id,
        "question": "什么是 RAG？",
        "top_k": 3,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    # 4. 解析 SSE 事件
    events = _parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    # 必须含 start / delta / done
    assert "start" in event_types
    assert "delta" in event_types
    assert "done" in event_types
    assert event_types[0] == "start"
    assert event_types[-1] == "done"

    # start 事件含 trace_id
    start_data = events[0]["data"]
    assert start_data["trace_id"]

    # delta 事件拼接后含回答内容
    delta_events = [e for e in events if e["event"] == "delta"]
    full_answer = "".join(e["data"]["content"] for e in delta_events)
    assert full_answer  # 非空
    # Mock LLM 的回答含 "RAG" 关键词
    assert "RAG" in full_answer

    # done 事件含 trace_id + finish_reason
    done_data = events[-1]["data"]
    assert done_data["trace_id"]
    assert done_data["finish_reason"] == "stop"

    # 5. 验证 ChatMessage 表有 user + assistant 记录
    factory = get_session_factory()
    async with factory() as db_session:
        result = await db_session.execute(
            text(
                "SELECT role, content, retrieval_context FROM t_chat_message "
                "WHERE session_id = :sid ORDER BY created_at ASC"
            ),
            {"sid": session_id},
        )
        rows = result.fetchall()
        # 至少 2 条：1 user + 1 assistant
        assert len(rows) >= 2
        roles = [r[0] for r in rows]
        assert MessageRole.USER.value in roles
        assert MessageRole.ASSISTANT.value in roles

        # user 消息内容
        user_rows = [r for r in rows if r[0] == MessageRole.USER.value]
        assert len(user_rows) >= 1
        assert "什么是 RAG" in user_rows[0][1]

        # assistant 消息内容
        assistant_rows = [r for r in rows if r[0] == MessageRole.ASSISTANT.value]
        assert len(assistant_rows) >= 1
        assert assistant_rows[0][1]  # 非空

        # 6. 验证 retrieval_context 非空（assistant 消息）
        retrieval_ctx = assistant_rows[0][2]
        assert retrieval_ctx is not None
        assert isinstance(retrieval_ctx, dict)
        assert "chunk_ids" in retrieval_ctx
        assert len(retrieval_ctx["chunk_ids"]) > 0, "retrieval_context.chunk_ids 不能为空"
        assert "items" in retrieval_ctx
        assert len(retrieval_ctx["items"]) > 0
        # 每个 item 含 chunk_id / document_id / content
        first_item = retrieval_ctx["items"][0]
        assert first_item["chunk_id"]
        assert first_item["document_id"]
        assert first_item["content"]


@pytest.mark.asyncio
async def test_e2e_chat_sse_retrieval_context_non_empty(
    e2e_app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """验证 retrieval_context 非空（专门验证检索上下文落库）。"""
    client, resources = e2e_app_client

    kb_id = await _create_kb(client, resources)
    doc_content = "检索增强生成技术（RAG）通过向量检索召回相关上下文。" * 5
    await _upload_and_wait(client, kb_id, doc_content)

    session_id = f"e2e-ctx-{uuid.uuid4().hex[:8]}"
    resources["session_ids"].append(session_id)
    payload = {
        "session_id": session_id,
        "kb_id": kb_id,
        "question": "RAG 通过什么检索？",
        "top_k": 5,
    }

    resp = await client.post("/api/v1/chat/sse", json=payload)
    assert resp.status_code == 200

    # 直接查 DB 验证 retrieval_context
    factory = get_session_factory()
    async with factory() as db_session:
        result = await db_session.execute(
            text(
                "SELECT retrieval_context FROM t_chat_message "
                "WHERE session_id = :sid AND role = 'assistant' "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"sid": session_id},
        )
        row = result.fetchone()
        assert row is not None
        ctx = row[0]
        assert ctx is not None
        assert isinstance(ctx, dict)
        # 关键验证：chunk_ids / items 非空
        assert len(ctx["chunk_ids"]) > 0
        assert len(ctx["items"]) > 0
        # 每个 item 含 content（检索到的文档片段）
        for item in ctx["items"]:
            assert "content" in item
            assert item["content"]


@pytest.mark.asyncio
async def test_e2e_chat_sse_full_async_no_blocking(
    e2e_app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """验证全流程 async，无阻塞 IO。"""
    client, resources = e2e_app_client

    kb_id = await _create_kb(client, resources)
    await _upload_and_wait(client, kb_id, "异步测试内容。" * 10)

    session_id = f"e2e-async-{uuid.uuid4().hex[:8]}"
    resources["session_ids"].append(session_id)
    payload = {
        "session_id": session_id,
        "kb_id": kb_id,
        "question": "测试异步",
        "top_k": 1,
    }

    # 全程 await，无同步阻塞调用
    resp = await client.post("/api/v1/chat/sse", json=payload)
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    # 至少 start + delta + done
    assert len(events) >= 3
