"""对话 Service：编排 load_history → retrieve → prompt → stream_chat → persist。

职责：
- 加载对话历史（Memory）
- 向量检索（Retriever + PostProcessor + Reranker）
- Prompt 渲染（PromptService）
- LLM 流式生成（stream_chat）
- 持久化 user + assistant 消息（含 retrieval_context）
- trace_id 透传（contextvars，不写 Span 树）

约束：
- 全 async，无阻塞 IO
- api 层只调用本 Service，不直接访问 retriever/llm/memory
- ChatService 不感知 HTTP 语义（异常由全局处理器转换）
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

from ragent.domain.dto import ChatChunk, ChatMessage, RetrievalResult
from ragent.domain.enums import MessageRole
from ragent.domain.value_objects import ChatOptions, RetrievalQuery
from ragent.framework.core.exceptions import BizException
from ragent.framework.core.logging import get_logger
from ragent.framework.trace.context import get_trace_id
from ragent.infra_ai.llm.base import BaseLLMClient
from ragent.infra_ai.rerank.base import BaseReranker
from ragent.persistence.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
)
from ragent.rag.memory.base import BaseMemoryStore
from ragent.rag.prompt.service import PromptService
from ragent.rag.retrieve.base import BaseRetriever
from ragent.rag.retrieve.postprocessor.base import BasePostProcessor

_logger = get_logger(__name__)

# 历史消息最大条数（MVP 固定，避免上下文过长）
_MAX_HISTORY_MESSAGES = 10
# 历史对话格式化时每条消息的前缀
_HISTORY_USER_PREFIX = "用户："
_HISTORY_ASSISTANT_PREFIX = "助手："


class ChatService:
    """对话编排 Service。

    编排流程（stream_chat）：
    1. 确保会话存在（get_or_create）
    2. load_history：加载最近 N 条历史
    3. retrieve：用 VectorRetriever 检索 top_k 候选
    4. postprocess：用 PostProcessor 链去重
    5. rerank：用 IdentityReranker 截断到最终 top_k（MVP 直通）
    6. prompt：用 PromptService 渲染 KB 问答模板
    7. stream_chat：LLM 流式生成，yield ChatChunk
    8. persist user：保存用户消息
    9. persist assistant：保存助手消息（含 retrieval_context），流结束后写入

    trace_id 通过 contextvars 透传，不写 Span 树。
    """

    def __init__(
        self,
        *,
        retriever: BaseRetriever,
        post_processors: list[BasePostProcessor],
        reranker: BaseReranker,
        llm_client: BaseLLMClient,
        memory_store: BaseMemoryStore,
        prompt_service: PromptService,
        chat_message_repo: ChatMessageRepository,
        chat_session_repo: ChatSessionRepository,
    ) -> None:
        """初始化 ChatService。

        Args:
            retriever: 检索器（VectorRetriever）
            post_processors: 后处理器链（按 order 升序执行）
            reranker: Rerank 客户端（MVP: IdentityReranker）
            llm_client: LLM 客户端
            memory_store: 对话记忆
            prompt_service: Prompt 模板服务
            chat_message_repo: 消息 Repository
            chat_session_repo: 会话 Repository
        """
        self._retriever = retriever
        # 按 order 升序排列，确保执行顺序确定
        self._post_processors = sorted(post_processors, key=lambda p: p.order())
        self._reranker = reranker
        self._llm_client = llm_client
        self._memory_store = memory_store
        self._prompt_service = prompt_service
        self._chat_message_repo = chat_message_repo
        self._chat_session_repo = chat_session_repo

    async def stream_chat(
        self,
        *,
        session_id: str,
        kb_id: str,
        question: str,
        top_k: int,
        options: ChatOptions | None = None,
    ) -> AsyncIterator[ChatChunk]:
        """流式问答：编排检索 + Prompt + LLM 流式 + 持久化。

        流程：
        1. 确保会话存在
        2. 加载历史
        3. 检索 + 后处理 + Rerank
        4. 渲染 Prompt
        5. LLM 流式生成，yield ChatChunk
        6. 流结束后持久化 user + assistant 消息

        Args:
            session_id: 会话 ID
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索 top_k
            options: 对话选项，None 时用默认

        Yields:
            ChatChunk（LLM 流式输出）

        Raises:
            BizException: 问题为空 / 知识库不存在
        """
        if not question or not question.strip():
            raise BizException(
                message="问题不能为空",
                code=10501,
            )

        chat_options = options or ChatOptions()
        trace_id = get_trace_id()
        start_ts = time.perf_counter()

        # 1. 确保会话存在
        await self._chat_session_repo.get_or_create(session_id, kb_id=kb_id)

        # 2. 加载历史
        history_messages = await self._memory_store.load_history(session_id, _MAX_HISTORY_MESSAGES)
        history_text = self._format_history(history_messages)

        # 3. 检索 + 后处理 + Rerank
        results = await self._retrieve_and_postprocess(kb_id, question, top_k)

        # 4. 渲染 Prompt
        evidence = self._build_evidence(results)
        prompt = self._prompt_service.render_answer_chat_kb(
            evidence=evidence,
            question=question,
            history=history_text,
        )

        # 构造 LLM messages：system 提示由 Prompt 模板内嵌，这里只传 user
        # 将渲染后的 prompt 作为单条 user 消息发给 LLM
        llm_messages = [ChatMessage(role=MessageRole.USER.value, content=prompt)]

        # 5. 持久化 user 消息（在 LLM 调用前写入，确保即使流式中断也有 user 记录）
        await self._chat_message_repo.append_message(
            session_id,
            ChatMessage(role=MessageRole.USER.value, content=question),
            trace_id=trace_id,
        )
        await self._chat_session_repo.increment_message_count(session_id, delta=1)
        await self._chat_message_repo.session.commit()

        # 6. LLM 流式生成 + 收集完整回复
        full_reply_parts: list[str] = []
        finish_reason: str | None = None
        try:
            async for chunk in self._llm_client.stream_chat(llm_messages, chat_options):
                if chunk.delta:
                    full_reply_parts.append(chunk.delta)
                if chunk.finish_reason is not None:
                    finish_reason = chunk.finish_reason
                yield chunk
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                "chat_stream_failed",
                session_id=session_id,
                kb_id=kb_id,
                error=str(exc),
                exc_info=True,
            )
            raise

        # 7. 流结束后持久化 assistant 消息（含 retrieval_context）
        full_reply = "".join(full_reply_parts)
        latency_ms = int((time.perf_counter() - start_ts) * 1000)
        retrieval_context = self._build_retrieval_context(results)

        await self._chat_message_repo.append_message(
            session_id,
            ChatMessage(role=MessageRole.ASSISTANT.value, content=full_reply),
            retrieval_context=retrieval_context,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )
        await self._chat_session_repo.increment_message_count(session_id, delta=1)
        await self._chat_message_repo.session.commit()

        _logger.info(
            "chat_stream_completed",
            session_id=session_id,
            kb_id=kb_id,
            retrieval_count=len(results),
            reply_chars=len(full_reply),
            finish_reason=finish_reason,
            latency_ms=latency_ms,
        )

    async def chat(
        self,
        *,
        session_id: str,
        kb_id: str,
        question: str,
        top_k: int,
        options: ChatOptions | None = None,
    ) -> str:
        """非流式问答（聚合 stream_chat 的全部 delta）。

        Args:
            session_id: 会话 ID
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索 top_k
            options: 对话选项

        Returns:
            完整回复文本
        """
        parts: list[str] = []
        async for chunk in self.stream_chat(
            session_id=session_id,
            kb_id=kb_id,
            question=question,
            top_k=top_k,
            options=options,
        ):
            if chunk.delta:
                parts.append(chunk.delta)
        return "".join(parts)

    async def _retrieve_and_postprocess(
        self,
        kb_id: str,
        question: str,
        top_k: int,
    ) -> list[RetrievalResult]:
        """检索 + 后处理 + Rerank。

        Args:
            kb_id: 知识库 ID
            question: 查询文本
            top_k: 检索 top_k

        Returns:
            处理后的检索结果列表
        """
        query = RetrievalQuery(text=question, kb_id=kb_id)
        # 检索时多取一些候选（top_k * 2），便于后处理去重后仍有足够结果
        retrieve_top_k = max(top_k, top_k * 2)
        results = await self._retriever.retrieve(query, retrieve_top_k)

        # 后处理器链（按 order 升序）
        for processor in self._post_processors:
            results = await processor.process(question, results)

        # Rerank 截断到最终 top_k（MVP: IdentityReranker 直通截断）
        if self._reranker.enabled():
            results = await self._reranker.rerank(question, results, top_k)

        _logger.info(
            "chat_retrieve_done",
            kb_id=kb_id,
            top_k=top_k,
            retrieved=len(results),
        )
        return results

    @staticmethod
    def _format_history(messages: list[ChatMessage]) -> str:
        """格式化历史对话为文本。

        Args:
            messages: 历史消息列表

        Returns:
            格式化后的历史文本（无历史时返回"(无)"）
        """
        if not messages:
            return "(无)"
        lines: list[str] = []
        for m in messages:
            if m.role == MessageRole.USER.value:
                lines.append(f"{_HISTORY_USER_PREFIX}{m.content}")
            elif m.role == MessageRole.ASSISTANT.value:
                lines.append(f"{_HISTORY_ASSISTANT_PREFIX}{m.content}")
            else:
                lines.append(f"{m.role}：{m.content}")
        return "\n".join(lines)

    def _build_evidence(self, results: list[RetrievalResult]) -> str:
        """把检索结果格式化为证据文本。

        Args:
            results: 检索结果列表

        Returns:
            证据文本（编号 + 内容）
        """
        if not results:
            return "(无相关证据)"
        items = [r.content for r in results]
        return self._prompt_service.format_evidence_items(items)

    @staticmethod
    def _build_retrieval_context(
        results: list[RetrievalResult],
    ) -> dict[str, Any]:
        """构造 retrieval_context 摘要，用于落库到 t_chat_message.retrieval_context。

        Args:
            results: 检索结果列表

        Returns:
            摘要 dict，含 chunk_ids / document_ids / scores / contents
        """
        if not results:
            return {
                "chunk_ids": [],
                "document_ids": [],
                "scores": [],
                "items": [],
            }
        return {
            "chunk_ids": [r.chunk_id for r in results],
            "document_ids": [r.document_id for r in results],
            "scores": [r.score for r in results],
            "items": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "kb_id": r.kb_id,
                    "score": r.score,
                    "content": r.content[:500],
                    "retrieval_channel": r.retrieval_channel,
                }
                for r in results
            ],
        }


__all__ = ["ChatService"]
