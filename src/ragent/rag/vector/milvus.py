"""Milvus 向量库实现。

使用 pymilvus AsyncMilvusClient（原生 async）。
collection schema：
  - id: VARCHAR(64) 主键（与 t_document_chunk.id 一致）
  - vector: FLOAT_VECTOR(dim)
  - content: VARCHAR(8192) 原始文本
  - document_id: VARCHAR(64) 文档 ID（用于按文档删除）
  - kb_id: VARCHAR(64) 知识库 ID（用于按 KB 过滤）
  - metadata: JSON 结构化元信息（page/heading 等）

实现类才允许依赖 pymilvus，base 接口（rag/vector/base.py）不依赖 pymilvus。
"""

from __future__ import annotations

import json
from typing import Any

from ragent.domain.dto import VectorHit, VectorRecord
from ragent.framework.core.config import get_settings
from ragent.framework.core.exceptions import InfraException
from ragent.framework.core.logging import get_logger
from ragent.rag.vector.base import BaseVectorStore

_logger = get_logger(__name__)

# Milvus 字段名常量
_FIELD_ID = "id"
_FIELD_VECTOR = "vector"
_FIELD_CONTENT = "content"
_FIELD_DOCUMENT_ID = "document_id"
_FIELD_KB_ID = "kb_id"
_FIELD_METADATA = "metadata"

# 内容字段最大长度（VARCHAR 需指定 max_length）
_CONTENT_MAX_LENGTH = 8192
_ID_MAX_LENGTH = 64
_METADATA_MAX_LENGTH = 4096


class MilvusVectorStore(BaseVectorStore):
    """Milvus 向量库实现。

    使用 pymilvus AsyncMilvusClient 原生 async 客户端。
    一个 MilvusVectorStore 实例对应一个 Milvus 部署，可管理多个 collection。
    """

    def __init__(
        self,
        uri: str | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        """初始化 Milvus 向量库。

        Args:
            uri: Milvus 连接 URI（如 http://localhost:19530），None 时从 Settings 读取
            client: 可注入的 AsyncMilvusClient 实例（测试用，便于 Mock）
        """
        self._uri = uri or get_settings().milvus.uri
        self._client = client
        self._owns_client = client is None

    async def _get_client(self) -> Any:
        """获取 AsyncMilvusClient（懒创建）。"""
        if self._client is None:
            # 延迟导入，避免模块加载时引入 pymilvus
            from pymilvus import AsyncMilvusClient

            self._client = AsyncMilvusClient(uri=self._uri)
            _logger.info("milvus_client_created", uri=self._uri)
        return self._client

    async def ensure_collection(self, collection_name: str, dim: int) -> None:
        """幂等创建 collection。

        若 collection 已存在则跳过；否则创建并建索引、加载。

        Args:
            collection_name: collection 名
            dim: 向量维度

        Raises:
            InfraException: Milvus 调用失败
        """
        if dim <= 0:
            raise ValueError(f"向量维度必须为正数，当前: {dim}")

        client = await self._get_client()

        try:
            already_exists = await client.has_collection(collection_name, timeout=10)
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus has_collection 失败: {collection_name} - {exc}",
                code=30020,
                cause=exc,
            ) from exc

        if already_exists:
            _logger.info("milvus_collection_already_exists", collection_name=collection_name)
            return

        # 构造 schema：id / vector / content / document_id / kb_id / metadata
        try:
            from pymilvus import DataType

            schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
            schema.add_field(_FIELD_ID, DataType.VARCHAR, is_primary=True, max_length=_ID_MAX_LENGTH)
            schema.add_field(
                _FIELD_VECTOR,
                DataType.FLOAT_VECTOR,
                dim=dim,
            )
            schema.add_field(_FIELD_CONTENT, DataType.VARCHAR, max_length=_CONTENT_MAX_LENGTH)
            schema.add_field(_FIELD_DOCUMENT_ID, DataType.VARCHAR, max_length=_ID_MAX_LENGTH)
            schema.add_field(_FIELD_KB_ID, DataType.VARCHAR, max_length=_ID_MAX_LENGTH)
            schema.add_field(_FIELD_METADATA, DataType.VARCHAR, max_length=_METADATA_MAX_LENGTH)

            # 索引参数：vector 字段建 IVF_FLAT 索引（COSINE 距离）
            index_params = _prepare_index_params(client, _FIELD_VECTOR)

            await client.create_collection(
                collection_name=collection_name,
                schema=schema,
                index_params=index_params,
            )
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus create_collection 失败: {collection_name} - {exc}",
                code=30021,
                cause=exc,
            ) from exc

        _logger.info(
            "milvus_collection_created",
            collection_name=collection_name,
            dim=dim,
        )

    async def upsert(self, collection_name: str, vectors: list[VectorRecord]) -> int:
        """批量写入/更新向量。

        Args:
            collection_name: collection 名
            vectors: 向量记录列表（id / vector / content / metadata）

        Returns:
            写入数量

        Raises:
            InfraException: Milvus 调用失败
        """
        if not vectors:
            return 0

        client = await self._get_client()

        rows: list[dict[str, Any]] = []
        for v in vectors:
            document_id = str(v.metadata.get("document_id", ""))
            kb_id = str(v.metadata.get("kb_id", ""))
            metadata_json = json.dumps(v.metadata, ensure_ascii=False)
            # 截断超长 content（避免超过 VARCHAR max_length）
            content = v.content[:_CONTENT_MAX_LENGTH]
            metadata_str = metadata_json[:_METADATA_MAX_LENGTH]
            rows.append(
                {
                    _FIELD_ID: v.id,
                    _FIELD_VECTOR: v.vector,
                    _FIELD_CONTENT: content,
                    _FIELD_DOCUMENT_ID: document_id,
                    _FIELD_KB_ID: kb_id,
                    _FIELD_METADATA: metadata_str,
                }
            )

        try:
            result = await client.upsert(collection_name=collection_name, data=rows)
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus upsert 失败: {collection_name} - {exc}",
                code=30022,
                cause=exc,
            ) from exc

        upsert_count = int(result.get("upsert_count", len(rows))) if isinstance(result, dict) else len(rows)

        _logger.info(
            "milvus_upsert_done",
            collection_name=collection_name,
            input_count=len(rows),
            upsert_count=upsert_count,
        )
        return upsert_count

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int,
        filter_expr: str | None = None,
    ) -> list[VectorHit]:
        """向量近邻检索。

        Args:
            collection_name: collection 名
            query_vector: 查询向量
            top_k: 返回前 K 条
            filter_expr: 过滤表达式（如 'document_id == "xxx"'），可空

        Returns:
            命中结果列表，按相似度从高到低排序

        Raises:
            InfraException: Milvus 调用失败
        """
        if top_k <= 0:
            return []

        client = await self._get_client()

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        output_fields = [_FIELD_CONTENT, _FIELD_DOCUMENT_ID, _FIELD_KB_ID, _FIELD_METADATA]

        try:
            # Milvus search 返回 List[List[dict]]（外层为查询数，内层为命中数）
            results = await client.search(
                collection_name=collection_name,
                data=[query_vector],
                limit=top_k,
                filter=filter_expr or "",
                search_params=search_params,
                output_fields=output_fields,
                timeout=30,
            )
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus search 失败: {collection_name} - {exc}",
                code=30023,
                cause=exc,
            ) from exc

        if not results:
            return []

        hits: list[VectorHit] = []
        for item in results[0]:
            entity = item.get("entity", {}) if isinstance(item, dict) else {}
            hit_id = str(item.get("id", "")) if isinstance(item, dict) else ""
            # Milvus COSINE 距离：值越大越相似（范围 [-1, 1]）
            distance = float(item.get("distance", 0.0)) if isinstance(item, dict) else 0.0
            content = str(entity.get(_FIELD_CONTENT, ""))
            metadata_str = str(entity.get(_FIELD_METADATA, "{}"))
            try:
                metadata = json.loads(metadata_str) if metadata_str else {}
            except (ValueError, TypeError):
                metadata = {}
            hits.append(
                VectorHit(
                    id=hit_id,
                    score=distance,
                    content=content,
                    metadata=metadata,
                )
            )

        _logger.info(
            "milvus_search_done",
            collection_name=collection_name,
            top_k=top_k,
            hit_count=len(hits),
        )
        return hits

    async def delete_by_document(self, collection_name: str, document_id: str) -> int:
        """按文档删除所有相关向量。

        Args:
            collection_name: collection 名
            document_id: 文档 ID

        Returns:
            删除数量

        Raises:
            InfraException: Milvus 调用失败
        """
        client = await self._get_client()
        filter_expr = f'{_FIELD_DOCUMENT_ID} == "{document_id}"'

        try:
            # 先查询数量（Milvus delete 不返回删除数，需先 count）
            # 使用 query 拿到 id 列表后删除
            result = await client.delete(
                collection_name=collection_name,
                filter=filter_expr,
                timeout=30,
            )
            delete_count = (
                int(result.get("delete_count", 0))
                if isinstance(result, dict)
                else 0
            )
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus delete_by_document 失败: {collection_name} document={document_id} - {exc}",
                code=30024,
                cause=exc,
            ) from exc

        _logger.info(
            "milvus_delete_done",
            collection_name=collection_name,
            document_id=document_id,
            delete_count=delete_count,
        )
        return delete_count

    async def drop_collection(self, collection_name: str) -> None:
        """删除 collection。

        Args:
            collection_name: collection 名

        Raises:
            InfraException: Milvus 调用失败
        """
        client = await self._get_client()
        try:
            await client.drop_collection(collection_name=collection_name, timeout=30)
        except Exception as exc:  # noqa: BLE001
            raise InfraException(
                message=f"Milvus drop_collection 失败: {collection_name} - {exc}",
                code=30025,
                cause=exc,
            ) from exc

        _logger.info("milvus_collection_dropped", collection_name=collection_name)

    async def close(self) -> None:
        """关闭客户端连接（自建实例才关闭）。"""
        if self._owns_client and self._client is not None:
            close_fn = getattr(self._client, "close", None)
            if close_fn is not None:
                result = close_fn()
                # close 可能是协程
                if hasattr(result, "__await__"):
                    await result
            self._client = None


def _prepare_index_params(client: Any, vector_field: str) -> Any:
    """构造 Milvus 索引参数。

    使用 IVF_FLAT + COSINE，适合中小规模（< 1M 向量）的 MVP 场景。
    """
    index_params = client.make_index_params()
    index_params.add_index(
        field_name=vector_field,
        index_type="IVF_FLAT",
        metric_type="COSINE",
        params={"nlist": 128},
    )
    return index_params


__all__ = ["MilvusVectorStore"]
