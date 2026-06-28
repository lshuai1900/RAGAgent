"""摄取 Pipeline：线性编排 parse → chunk → embed → index。

职责：
- parse：用 BaseDocumentParser 解析文件为 ParsedDocument
- chunk：用 BaseChunker 切分为 ChunkDraft 列表
- embed：用 BaseEmbeddingClient 批量向量化
- index：用 BaseVectorStore 写入 Milvus + 同步元数据到 PostgreSQL

Pipeline 不持有 DB session，依赖外部传入 repository 实例。
Pipeline 不感知 HTTP 语义，由 service 层编排。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ragent.domain.dto import ChunkDraft, ParsedDocument, VectorRecord
from ragent.domain.enums import ChunkEmbeddingStatus
from ragent.framework.core.logging import get_logger
from ragent.infra_ai.embedding.base import BaseEmbeddingClient
from ragent.ingestion.chunker.base import BaseChunker
from ragent.ingestion.chunker.recursive import RecursiveChunker
from ragent.ingestion.parser.base import BaseDocumentParser
from ragent.ingestion.parser.registry import get_parser
from ragent.rag.vector.base import BaseVectorStore

if TYPE_CHECKING:
    from ragent.persistence.models.chunk import DocumentChunk
    from ragent.persistence.repositories.chunk_repo import DocumentChunkRepository

_logger = get_logger(__name__)


class IngestionPipeline:
    """摄取 Pipeline。

    线性编排 4 个阶段：parse → chunk → embed → index。
    每个阶段独立可替换（依赖 base 接口，不依赖具体实现）。
    """

    def __init__(
        self,
        *,
        parser: BaseDocumentParser | None = None,
        chunker: BaseChunker | None = None,
        embedding_client: BaseEmbeddingClient,
        vector_store: BaseVectorStore,
    ) -> None:
        """初始化 Pipeline。

        Args:
            parser: 文档解析器，None 时通过 registry 按 file_type 路由
            chunker: 分块器，None 时使用 RecursiveChunker（默认策略）
            embedding_client: Embedding 客户端
            vector_store: 向量库
        """
        self._parser = parser
        self._chunker = chunker or RecursiveChunker()
        self._embedding_client = embedding_client
        self._vector_store = vector_store

    @property
    def vector_store(self) -> BaseVectorStore:
        """暴露 vector_store 供 service 层调用 ensure_collection。"""
        return self._vector_store

    @property
    def embedding_client(self) -> BaseEmbeddingClient:
        """暴露 embedding_client 供 service 层读取维度信息。"""
        return self._embedding_client

    async def parse(self, file_path: Path, file_type: str) -> ParsedDocument:
        """阶段 1：解析文档。

        Args:
            file_path: 文件路径
            file_type: 文件类型

        Returns:
            ParsedDocument
        """
        parser = self._parser or get_parser(file_type)
        parsed = await parser.parse(file_path, file_type)
        _logger.info(
            "pipeline_parse_done",
            file_path=str(file_path),
            file_type=file_type,
            char_count=len(parsed.text),
            section_count=len(parsed.sections),
        )
        return parsed

    async def chunk(
        self,
        parsed: ParsedDocument,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[ChunkDraft]:
        """阶段 2：分块。

        Args:
            parsed: 解析后的文档
            chunk_size: 分块大小
            chunk_overlap: 分块重叠

        Returns:
            ChunkDraft 列表
        """
        # 延迟导入避免循环依赖
        from ragent.domain.value_objects import ChunkConfig

        config = ChunkConfig(chunk_size=chunk_size, overlap=chunk_overlap)
        chunks = await self._chunker.chunk(parsed, config)
        _logger.info(
            "pipeline_chunk_done",
            chunk_count=len(chunks),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return chunks

    async def embed(self, chunks: list[ChunkDraft]) -> list[list[float]]:
        """阶段 3：批量向量化。

        Args:
            chunks: 分块列表

        Returns:
            向量列表，顺序与 chunks 一致
        """
        if not chunks:
            return []
        texts = [c.content for c in chunks]
        vectors = await self._embedding_client.embed(texts)
        _logger.info(
            "pipeline_embed_done",
            chunk_count=len(chunks),
            vector_count=len(vectors),
            model=self._embedding_client.model_name(),
            dim=self._embedding_client.dim(),
        )
        return vectors

    async def index(
        self,
        collection_name: str,
        chunks: list[ChunkDraft],
        vectors: list[list[float]],
        *,
        document_id: str,
        kb_id: str,
        chunk_repo: DocumentChunkRepository,
    ) -> int:
        """阶段 4：写入 Milvus + 同步元数据到 PostgreSQL。

        Args:
            collection_name: Milvus collection 名
            chunks: 分块草稿列表
            vectors: 与 chunks 一一对应的向量
            document_id: 文档 ID
            kb_id: 知识库 ID
            chunk_repo: 分块 Repository（用于写 PostgreSQL 元数据）

        Returns:
            索引的分块数
        """
        from ragent.persistence.models.chunk import DocumentChunk

        if not chunks:
            return 0

        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks 与 vectors 数量不一致: chunks={len(chunks)} vectors={len(vectors)}"
            )

        # 1. 写 PostgreSQL 元数据（chunk.id 由雪花生成器产生）
        chunk_entities: list[DocumentChunk] = []
        for chunk, _vector in zip(chunks, vectors, strict=True):
            # 合并 metadata：分块器原始 metadata + document_id + kb_id（便于 Milvus 过滤）
            metadata = dict(chunk.metadata)
            metadata["document_id"] = document_id
            metadata["kb_id"] = kb_id

            entity = DocumentChunk(
                document_id=document_id,
                kb_id=kb_id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                token_count=self._estimate_tokens(chunk.content),
                char_count=len(chunk.content),
                chunk_metadata=metadata,
                embedding_status=ChunkEmbeddingStatus.PENDING.value,
            )
            chunk_entities.append(entity)

        await chunk_repo.add_batch(chunk_entities)

        # 2. 构造 VectorRecord 列表（chunk.id 与 Milvus 主键一致）
        records: list[VectorRecord] = []
        for entity, vector in zip(chunk_entities, vectors, strict=True):
            metadata = dict(entity.chunk_metadata)
            records.append(
                VectorRecord(
                    id=entity.id,
                    vector=vector,
                    content=entity.content,
                    metadata=metadata,
                )
            )

        # 3. 写 Milvus
        upserted = await self._vector_store.upsert(collection_name, records)

        # 4. 更新分块 Embedding 状态为 indexed
        chunk_ids = [c.id for c in chunk_entities]
        await chunk_repo.update_embedding_status_batch(
            chunk_ids, ChunkEmbeddingStatus.INDEXED.value
        )

        _logger.info(
            "pipeline_index_done",
            collection_name=collection_name,
            document_id=document_id,
            chunk_count=len(chunks),
            upserted=upserted,
        )
        return len(chunk_entities)

    async def run(
        self,
        *,
        file_path: Path,
        file_type: str,
        document_id: str,
        kb_id: str,
        collection_name: str,
        chunk_size: int,
        chunk_overlap: int,
        chunk_repo: DocumentChunkRepository,
    ) -> int:
        """端到端运行 pipeline：parse → chunk → embed → index。

        Args:
            file_path: 文件路径
            file_type: 文件类型
            document_id: 文档 ID
            kb_id: 知识库 ID
            collection_name: Milvus collection 名
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            chunk_repo: 分块 Repository

        Returns:
            索引的分块数
        """
        parsed = await self.parse(file_path, file_type)
        chunks = await self.chunk(parsed, chunk_size, chunk_overlap)
        vectors = await self.embed(chunks)
        indexed = await self.index(
            collection_name,
            chunks,
            vectors,
            document_id=document_id,
            kb_id=kb_id,
            chunk_repo=chunk_repo,
        )
        return indexed

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """粗略估算 token 数。

        中文按 1 字 ≈ 1.5 token，英文按 4 字符 ≈ 1 token。
        MVP 不引入 tiktoken，估算即可。
        """
        if not text:
            return 0
        chinese_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other_count = len(text) - chinese_count
        return int(chinese_count * 1.5 + other_count / 4)


__all__ = ["IngestionPipeline"]
