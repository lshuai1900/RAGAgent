"""T9 知识库 + 文档 API 集成测试。

依赖 docker-compose 启动的 PostgreSQL + Milvus。
Embedding 客户端用 Mock（避免真实调用外部模型）。

覆盖：
- POST /api/v1/knowledge-bases：创建 KB
- GET /api/v1/knowledge-bases：列出 KB
- GET /api/v1/knowledge-bases/{kb_id}：查询 KB
- POST /api/v1/documents/upload：上传文档，立即返回 document_id（status=pending）
- GET /api/v1/documents：列出文档
- GET /api/v1/documents/{document_id}：查询文档状态
- SHA256 去重
- 不支持的文件类型
- 不存在的知识库
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

from ragent.framework.core.config import reload_settings
from ragent.framework.db.session import (
    dispose_engine,
    get_engine,
    get_session_factory,
)
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.ingestion.pipeline import IngestionPipeline
from ragent.main import create_app
from ragent.rag.vector.base import BaseVectorStore
from ragent.rag.vector.milvus import MilvusVectorStore

# Mock Embedding 维度（与 KB 创建请求的 embedding_dim 一致）
_MOCK_DIM = 8


# ---------- Mock Embedding Client ----------


class MockEmbeddingClient:
    """Mock Embedding 客户端：返回确定性向量，避免真实调用。"""

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
        h = abs(hash(text)) % 100
        return [float((h + i) % 10) / 10.0 for i in range(self._dim)]


# ---------- Fixtures ----------


@pytest.fixture
async def app_client(
    postgres_available: bool,
    milvus_available: bool,
) -> AsyncIterator[tuple[httpx.AsyncClient, dict[str, Any]]]:
    """构造 ASGI 测试客户端 + 共享资源句柄。

    Yields:
        (client, cleanup_resources)
        - client: httpx.AsyncClient
        - cleanup_resources: 用于测试结束后清理的集合（含已创建 KB 的 collection_name）

    通过 FastAPI `dependency_overrides` 注入 Mock Embedding 客户端，
    共享 MilvusVectorStore 实例（便于测试后清理 collection）。
    """
    # 重置 settings + engine + 单例
    reload_settings()
    await dispose_engine()

    # 验证表已迁移
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT to_regclass('t_knowledge_base')"))
        if result.scalar() is None:
            pytest.skip("数据库表未迁移，请先执行 alembic upgrade head")

    # 共享 Mock Embedding + Real Milvus
    mock_embedding = MockEmbeddingClient(dim=_MOCK_DIM)
    vector_store = MilvusVectorStore()
    pipeline = IngestionPipeline(
        embedding_client=mock_embedding,
        vector_store=vector_store,
    )

    app = create_app()

    # 通过 dependency_overrides 注入 Mock，覆盖 deps 单例
    # 注意：必须使用原 deps 函数引用作为 key（FastAPI 通过引用匹配依赖）
    from fastapi import Depends

    from ragent.api.deps import (
        get_document_repo as _orig_get_document_repo,
    )
    from ragent.api.deps import (
        get_embedding_client as _orig_get_embedding_client,
    )
    from ragent.api.deps import (
        get_ingestion_service as _orig_get_ingestion_service,
    )
    from ragent.api.deps import (
        get_kb_repo as _orig_get_kb_repo,
    )
    from ragent.api.deps import (
        get_knowledge_service as _orig_get_knowledge_service,
    )
    from ragent.api.deps import (
        get_pipeline as _orig_get_pipeline,
    )
    from ragent.api.deps import (
        get_vector_store as _orig_get_vector_store,
    )
    from ragent.persistence.repositories.document_repo import DocumentRepository
    from ragent.persistence.repositories.knowledge_base_repo import KnowledgeBaseRepository
    from ragent.service.ingestion_service import IngestionService
    from ragent.service.knowledge_service import KnowledgeService

    def _override_embedding() -> BaseEmbeddingClient:
        return mock_embedding

    def _override_vector_store() -> BaseVectorStore:
        return vector_store

    def _override_pipeline() -> IngestionPipeline:
        return pipeline

    def _override_knowledge_service(
        kb_repo: KnowledgeBaseRepository = Depends(_orig_get_kb_repo),
    ) -> KnowledgeService:
        return KnowledgeService(
            kb_repo=kb_repo,
            vector_store=vector_store,
            embedding_client=mock_embedding,
        )

    def _override_ingestion_service(
        kb_repo: KnowledgeBaseRepository = Depends(_orig_get_kb_repo),
        document_repo: DocumentRepository = Depends(_orig_get_document_repo),
    ) -> IngestionService:
        return IngestionService(
            kb_repo=kb_repo,
            document_repo=document_repo,
            pipeline=pipeline,
        )

    app.dependency_overrides[_orig_get_embedding_client] = _override_embedding
    app.dependency_overrides[_orig_get_vector_store] = _override_vector_store
    app.dependency_overrides[_orig_get_pipeline] = _override_pipeline
    app.dependency_overrides[_orig_get_knowledge_service] = _override_knowledge_service
    app.dependency_overrides[_orig_get_ingestion_service] = _override_ingestion_service

    transport = ASGITransport(app=app)
    cleanup_resources: dict[str, Any] = {
        "vector_store": vector_store,
        "collections": [],  # 已创建的 collection 名列表
        "kb_ids": [],  # 已创建的 KB ID 列表
    }

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://test") as c,
    ):
        yield c, cleanup_resources

    # 清理 dependency_overrides
    app.dependency_overrides.clear()

    # 清理 Milvus collections
    for coll_name in cleanup_resources["collections"]:
        with contextlib.suppress(Exception):
            await vector_store.drop_collection(coll_name)

    # 清理 PostgreSQL
    factory = get_session_factory()
    async with factory() as session:
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


# ---------- KB API ----------


@pytest.mark.asyncio
async def test_create_knowledge_base(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """POST /api/v1/knowledge-bases 创建知识库。"""
    client, resources = app_client
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"test-kb-{unique}",
        "description": "测试知识库",
        "embedding_model": "mock-embedding",
        "embedding_dim": _MOCK_DIM,
        "chunk_strategy": "recursive",
        "chunk_size": 512,
        "chunk_overlap": 64,
    }

    resp = await client.post("/api/v1/knowledge-bases", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["name"] == payload["name"]
    assert data["embedding_dim"] == _MOCK_DIM
    assert data["status"] == "active"
    assert data["collection_name"].startswith("kb_")

    resources["kb_ids"].append(data["id"])
    resources["collections"].append(data["collection_name"])


@pytest.mark.asyncio
async def test_create_kb_duplicate_name_raises(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """重复名称：返回 BizException。"""
    client, resources = app_client
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"dup-kb-{unique}",
        "embedding_dim": _MOCK_DIM,
    }

    # 第一次成功
    resp1 = await client.post("/api/v1/knowledge-bases", json=payload)
    assert resp1.status_code == 201
    resources["kb_ids"].append(resp1.json()["data"]["id"])
    resources["collections"].append(resp1.json()["data"]["collection_name"])

    # 第二次冲突
    resp2 = await client.post("/api/v1/knowledge-bases", json=payload)
    assert resp2.status_code == 400
    body = resp2.json()
    assert body["code"] == 10101


@pytest.mark.asyncio
async def test_create_kb_dim_mismatch_raises(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """embedding_dim 与客户端不一致：返回 BizException。"""
    client, _ = app_client
    payload = {
        "name": f"dim-mismatch-{uuid.uuid4().hex[:8]}",
        "embedding_dim": 999,  # 与 Mock（8）不一致
    }

    resp = await client.post("/api/v1/knowledge-bases", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10102


@pytest.mark.asyncio
async def test_list_knowledge_bases(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """GET /api/v1/knowledge-bases 分页列出。"""
    client, resources = app_client

    # 创建 2 个 KB
    for i in range(2):
        payload = {
            "name": f"list-kb-{uuid.uuid4().hex[:8]}-{i}",
            "embedding_dim": _MOCK_DIM,
        }
        resp = await client.post("/api/v1/knowledge-bases", json=payload)
        assert resp.status_code == 201
        resources["kb_ids"].append(resp.json()["data"]["id"])
        resources["collections"].append(resp.json()["data"]["collection_name"])

    resp = await client.get("/api/v1/knowledge-bases?page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 10
    assert len(body["data"]["items"]) >= 2


@pytest.mark.asyncio
async def test_get_knowledge_base_by_id(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """GET /api/v1/knowledge-bases/{kb_id}。"""
    client, resources = app_client
    payload = {
        "name": f"get-kb-{uuid.uuid4().hex[:8]}",
        "embedding_dim": _MOCK_DIM,
    }
    create_resp = await client.post("/api/v1/knowledge-bases", json=payload)
    kb_id = create_resp.json()["data"]["id"]
    resources["kb_ids"].append(kb_id)
    resources["collections"].append(create_resp.json()["data"]["collection_name"])

    resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == kb_id


@pytest.mark.asyncio
async def test_get_kb_not_found_raises(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """查询不存在的 KB：返回 BizException。"""
    client, _ = app_client
    fake_id = "non-existent-kb-id"

    resp = await client.get(f"/api/v1/knowledge-bases/{fake_id}")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10404


# ---------- Document Upload API ----------


async def _create_kb(
    client: httpx.AsyncClient,
    resources: dict[str, Any],
) -> str:
    """辅助：创建测试 KB 并返回 kb_id。"""
    payload = {
        "name": f"upload-kb-{uuid.uuid4().hex[:8]}",
        "embedding_dim": _MOCK_DIM,
    }
    resp = await client.post("/api/v1/knowledge-bases", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    resources["kb_ids"].append(data["id"])
    resources["collections"].append(data["collection_name"])
    return data["id"]


@pytest.mark.asyncio
async def test_upload_txt_document(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """POST /api/v1/documents/upload 上传 TXT：立即返回 document_id（status=pending）。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    content = "测试文本内容。这是用于上传测试的文档。" * 10
    files = {"file": ("demo.txt", content.encode("utf-8"), "text/plain")}
    data = {"kb_id": kb_id}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)

    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 0
    response_data = body["data"]
    assert response_data["document_id"]
    assert response_data["kb_id"] == kb_id
    assert response_data["name"] == "demo.txt"
    assert response_data["file_type"] == "txt"
    assert response_data["file_hash"]
    assert response_data["duplicated"] is False
    # 立即返回时 status 应为 pending
    assert response_data["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_md_document(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """POST /api/v1/documents/upload 上传 MD。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    content = "# 标题\n内容一\n\n## 子标题\n内容二\n"
    files = {"file": ("demo.md", content.encode("utf-8"), "text/markdown")}
    data = {"kb_id": kb_id}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)

    assert resp.status_code == 201
    assert resp.json()["data"]["file_type"] == "md"


@pytest.mark.asyncio
async def test_upload_pdf_document(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """POST /api/v1/documents/upload 上传 PDF。"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("reportlab 未安装，跳过 PDF 上传测试")

    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    import io

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(100, 750, "PDF test content page 1")
    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()

    files = {"file": ("demo.pdf", pdf_bytes, "application/pdf")}
    data = {"kb_id": kb_id}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)

    assert resp.status_code == 201
    assert resp.json()["data"]["file_type"] == "pdf"


@pytest.mark.asyncio
async def test_upload_duplicated_document(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """相同 SHA256 重复上传：返回 duplicated=True 与原 document_id。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    content = "重复内容测试。" * 5
    files = {"file": ("dup.txt", content.encode("utf-8"), "text/plain")}
    data = {"kb_id": kb_id}

    resp1 = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert resp1.status_code == 201
    doc_id_1 = resp1.json()["data"]["document_id"]

    # 再次上传相同内容
    files2 = {"file": ("dup_copy.txt", content.encode("utf-8"), "text/plain")}
    resp2 = await client.post("/api/v1/documents/upload", files=files2, data=data)
    assert resp2.status_code == 201
    body2 = resp2.json()["data"]
    assert body2["duplicated"] is True
    assert body2["document_id"] == doc_id_1


@pytest.mark.asyncio
async def test_upload_unsupported_file_type(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """不支持的文件类型：返回 BizException。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    files = {"file": ("demo.docx", b"fake docx content", "application/octet-stream")}
    data = {"kb_id": kb_id}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10201


@pytest.mark.asyncio
async def test_upload_to_nonexistent_kb(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """上传到不存在的 KB：返回 BizException。"""
    client, _ = app_client

    files = {"file": ("demo.txt", b"content", "text/plain")}
    data = {"kb_id": "non-existent-kb"}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10404


@pytest.mark.asyncio
async def test_upload_empty_file_raises(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """空文件：返回 BizException。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    files = {"file": ("empty.txt", b"", "text/plain")}
    data = {"kb_id": kb_id}

    resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10203


# ---------- Document Status API ----------


@pytest.mark.asyncio
async def test_get_document_status(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """GET /api/v1/documents/{document_id} 查询文档状态。

    等待 BackgroundTasks 执行完成，验证 status 变为 completed。
    """
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    content = "查询状态测试。这是用于测试文档状态查询的内容。" * 20
    files = {"file": ("status.txt", content.encode("utf-8"), "text/plain")}
    data = {"kb_id": kb_id}

    upload_resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    assert upload_resp.status_code == 201
    document_id = upload_resp.json()["data"]["document_id"]

    # 立即查询应返回 pending 或进行中状态
    immediate_resp = await client.get(f"/api/v1/documents/{document_id}")
    assert immediate_resp.status_code == 200
    immediate_status = immediate_resp.json()["data"]["status"]
    assert immediate_status in {
        "pending",
        "parsing",
        "chunking",
        "embedding",
        "indexing",
        "completed",
    }

    # 轮询等待 BackgroundTasks 完成（最长 10 秒）
    final_status = immediate_status
    for _ in range(20):
        await asyncio.sleep(0.5)
        resp = await client.get(f"/api/v1/documents/{document_id}")
        assert resp.status_code == 200
        final_status = resp.json()["data"]["status"]
        if final_status in {"completed", "failed"}:
            break

    # 最终状态应为 completed（Mock Embedding 不会失败）
    assert final_status == "completed", (
        f"文档状态未变为 completed，实际: {final_status}, error: {immediate_resp.json()}"
    )


@pytest.mark.asyncio
async def test_get_document_not_found(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """查询不存在的文档：返回 BizException。"""
    client, _ = app_client

    resp = await client.get("/api/v1/documents/non-existent-doc")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == 10304


@pytest.mark.asyncio
async def test_list_documents(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """GET /api/v1/documents 列出文档（可按 kb_id 过滤）。"""
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    # 上传 2 个文档
    for i in range(2):
        files = {
            "file": (
                f"list-{i}.txt",
                f"内容 {i} " * 10,
                "text/plain",
            )
        }
        data = {"kb_id": kb_id}
        resp = await client.post("/api/v1/documents/upload", files=files, data=data)
        assert resp.status_code == 201

    # 按 kb_id 过滤
    resp = await client.get(f"/api/v1/documents?kb_id={kb_id}&page=1&page_size=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]["items"]) >= 2
    assert body["data"]["total"] >= 2


@pytest.mark.asyncio
async def test_upload_and_verify_milvus_written(
    app_client: tuple[httpx.AsyncClient, dict[str, Any]],
) -> None:
    """上传文档后，验证 Milvus 已写入向量。

    流程：
    1. 上传文档，等待 BackgroundTasks 完成
    2. 查询文档状态为 completed
    3. 通过 vector_store 直接查询 Milvus，确认向量已写入
    """
    client, resources = app_client
    kb_id = await _create_kb(client, resources)

    content = "验证 Milvus 写入测试。" * 20
    files = {"file": ("verify_milvus.txt", content.encode("utf-8"), "text/plain")}
    data = {"kb_id": kb_id}
    upload_resp = await client.post("/api/v1/documents/upload", files=files, data=data)
    document_id = upload_resp.json()["data"]["document_id"]

    # 轮询等待完成
    final_status = "pending"
    for _ in range(20):
        await asyncio.sleep(0.5)
        resp = await client.get(f"/api/v1/documents/{document_id}")
        final_status = resp.json()["data"]["status"]
        if final_status in {"completed", "failed"}:
            break

    assert final_status == "completed", f"文档未完成，状态: {final_status}"

    # 查询 KB 拿到 collection_name
    kb_resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}")
    collection_name = kb_resp.json()["data"]["collection_name"]

    # 通过 vector_store 查询 Milvus（按 document_id 过滤）
    vector_store: MilvusVectorStore = resources["vector_store"]
    query_vector = [0.5] * _MOCK_DIM  # 任意查询向量
    hits = await vector_store.search(
        collection_name,
        query_vector,
        top_k=100,
        filter_expr=f'document_id == "{document_id}"',
    )

    # 应能命中至少 1 条向量
    assert len(hits) >= 1, "Milvus 未写入任何向量"
    for hit in hits:
        assert hit.metadata.get("document_id") == document_id
