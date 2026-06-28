"""IngestionService 失败路径单元测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ragent.domain.dto import ChunkDraft, ParsedDocument
from ragent.domain.enums import DocumentStatus
from ragent.framework.core.exceptions import InfraException
from ragent.service import ingestion_service as ingestion_service_module
from ragent.service.ingestion_service import IngestionService


class _FakeSession:
    commits = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    async def commit(self) -> None:
        type(self).commits += 1


class _FakeDocumentRepository:
    status_updates: list[tuple[str, str, str | None]] = []

    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    async def update_status(
        self,
        document_id: str,
        status: str,
        *,
        error_message: str | None = None,
        chunk_count: int | None = None,
    ) -> None:
        _ = chunk_count
        self.status_updates.append((document_id, status, error_message))


class _FakeChunkRepository:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session


class _FakeKnowledgeBaseRepository:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session


class _FailingEmbeddingPipeline:
    vector_store = SimpleNamespace()

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        _ = (file_path, file_type)
        return ParsedDocument(text="hello", sections=[], metadata={})

    async def chunk(self, parsed: ParsedDocument, chunk_size: int, chunk_overlap: int) -> list[ChunkDraft]:
        _ = (parsed, chunk_size, chunk_overlap)
        return [ChunkDraft(content="hello", chunk_index=0, metadata={})]

    async def embed(self, chunks: list[ChunkDraft]) -> list[list[float]]:
        _ = chunks
        raise InfraException(
            message="Embedding API 调用失败 (HTTP 400): input data length exceeds max limit",
            code=30010,
        )


@pytest.mark.asyncio
async def test_pipeline_failure_saves_embedding_error_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """embedding 抛错后，后台任务保存 failed 状态和真实失败原因。"""
    _FakeDocumentRepository.status_updates = []
    _FakeSession.commits = 0

    monkeypatch.setattr(ingestion_service_module, "DocumentRepository", _FakeDocumentRepository)
    monkeypatch.setattr(ingestion_service_module, "DocumentChunkRepository", _FakeChunkRepository)
    monkeypatch.setattr(ingestion_service_module, "KnowledgeBaseRepository", _FakeKnowledgeBaseRepository)
    monkeypatch.setattr(ingestion_service_module, "get_session_factory", lambda: _FakeSession)

    file_path = tmp_path / "doc.md"
    file_path.write_text("# title\nhello", encoding="utf-8")
    temp_dir = tmp_path / "upload"
    temp_dir.mkdir()

    service = IngestionService(
        kb_repo=object(),  # type: ignore[arg-type]
        document_repo=object(),  # type: ignore[arg-type]
        pipeline=_FailingEmbeddingPipeline(),  # type: ignore[arg-type]
    )

    await service._run_pipeline_async(
        kb_id="kb-1",
        document_id="doc-1",
        collection_name="kb_1",
        chunk_size=512,
        chunk_overlap=64,
        file_path=str(file_path),
        file_type="md",
        temp_dir=str(temp_dir),
    )

    assert _FakeDocumentRepository.status_updates[-1] == (
        "doc-1",
        DocumentStatus.FAILED.value,
        "Embedding API 调用失败 (HTTP 400): input data length exceeds max limit",
    )
