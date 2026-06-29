<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 8：Yuxi 风格 RAG 聊天面板，复用 Step 7 的 SSE 客户端与 SourceCard。
-->
<script setup lang="ts">
/**
 * RAG 聊天面板（Step 8）
 *
 * - 自包含：本地消息状态，不共享 chat store（避免与检索测试串状态）
 * - 复用 streamChatSse（fetch + ReadableStream）+ mapCitationsToReferences + SourceReferenceCard
 * - AbortController 支持停止生成与离开页面中断
 * - 不实现会话历史；session_id 每次面板挂载时生成
 * - embedded=true 时不显示大标题（详情页已有 Header）
 *
 * 被 /chat（顶层）与 /knowledge-bases/:kbId/chat（详情页 Chat Tab）复用。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Button, Input, message } from 'ant-design-vue'
import {
  MessageSquare,
  RefreshCw,
  Send,
  Square,
} from 'lucide-vue-next'
import { streamChatSse } from '@/api/chat'
import YuxiEmptyState from '@/components/yuxi/YuxiEmptyState.vue'
import ChatMessageBubble from '@/components/chat/ChatMessageBubble.vue'
import { mapCitationsToReferences, type ChatMessage, type UiChatReference } from '@/utils/chatReferences'
import { formatChatStreamError } from '@/utils/apiErrors'
import type { ChatSseRequest } from '@/types/api'

interface Props {
  /** 当前知识库 ID（必填） */
  kbId: string
  /** 是否嵌入式（详情页 Chat Tab），true 时不显示大标题 */
  embedded?: boolean
  /** 标题，默认"聊天问答" */
  title?: string
  /** 描述文案 */
  description?: string
}
const props = withDefaults(defineProps<Props>(), {
  embedded: false,
})

/** 问题最大长度 */
const MAX_QUESTION_LEN = 2000
/** 默认 top_k */
const DEFAULT_TOP_K = 5

const question = ref('')
const messages = ref<ChatMessage[]>([])
const isSending = ref(false)
const isReceiving = ref(false)

let abortController: AbortController | null = null
let sessionId = genSessionId()

/** 消息列表滚动容器 */
const messagesContainer = ref<HTMLElement | null>(null)

const isStreaming = computed(() => isSending.value || isReceiving.value)
const canSend = computed(
  () => !isStreaming.value && question.value.trim().length > 0 && !!props.kbId,
)
const hasMessages = computed(() => messages.value.length > 0)

const headerTitle = computed(() => props.title ?? '聊天问答')
const headerDesc = computed(
  () => props.description ?? '选择知识库后进行 RAG 问答，回答将展示引用来源',
)

/** 生成临时 session_id（不保存到会话历史） */
function genSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `ragagent-chat-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 生成消息主键 */
function genMsgId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 当前 ISO 时间 */
function nowIso(): string {
  return new Date().toISOString()
}

/** 错误映射（中文）由 utils/apiErrors.ts 统一提供 */
/** SSE error 事件错误映射（后端 error 事件已有中文 message 时直接用） */
function mapSseError(data: { message: string; trace_id: string }): string {
  return data.message || '生成失败'
}

/** 滚动到底部 */
function scrollToBottom(): void {
  nextTick(() => {
    const el = messagesContainer.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

async function handleSend(): Promise<void> {
  const q = question.value.trim()
  if (!q) {
    message.warning('请输入问题')
    return
  }
  if (!props.kbId) {
    message.warning('请先选择知识库')
    return
  }
  if (isStreaming.value) return

  // 追加用户消息
  const userMsg: ChatMessage = {
    id: genMsgId(),
    role: 'user',
    content: q,
    createdAt: nowIso(),
  }
  messages.value.push(userMsg)

  // 追加助手占位消息（streaming 态）
  const assistantId = genMsgId()
  const assistantMsg: ChatMessage = {
    id: assistantId,
    role: 'assistant',
    content: '',
    createdAt: nowIso(),
    streaming: true,
    references: [],
  }
  messages.value.push(assistantMsg)

  question.value = ''
  isSending.value = true
  scrollToBottom()

  const payload: ChatSseRequest = {
    session_id: sessionId,
    kb_id: props.kbId,
    question: q,
    top_k: DEFAULT_TOP_K,
  }

  abortController?.abort()
  abortController = new AbortController()

  /** 是否已收到终态事件 */
  let receivedTerminal = false

  try {
    await streamChatSse(
      payload,
      {
        onStart: (data) => {
          isSending.value = false
          isReceiving.value = true
          patchAssistant(assistantId, { traceId: data.trace_id })
        },
        onDelta: (data) => {
          isSending.value = false
          isReceiving.value = true
          const cur = findAssistant(assistantId)
          if (cur) {
            cur.content += data.content
            scrollToBottom()
          }
        },
        onDone: (data) => {
          const refs: UiChatReference[] = mapCitationsToReferences(data)
          patchAssistant(assistantId, {
            streaming: false,
            traceId: data.trace_id || undefined,
            finishReason: data.finish_reason || '',
            references: refs,
          })
          receivedTerminal = true
          isSending.value = false
          isReceiving.value = false
        },
        onError: (data) => {
          patchAssistant(assistantId, {
            streaming: false,
            error: mapSseError(data),
            traceId: data.trace_id || undefined,
          })
          receivedTerminal = true
          isSending.value = false
          isReceiving.value = false
        },
      },
      abortController.signal,
    )

    // 流正常结束但未收到 done / error：视为中断
    if (!receivedTerminal) {
      patchAssistant(assistantId, {
        streaming: false,
        error: '流式响应解析失败，请稍后重试',
      })
      isSending.value = false
      isReceiving.value = false
    }
  } catch (err) {
    const { msg, trace } = formatChatStreamError(err)
    patchAssistant(assistantId, {
      streaming: false,
      error: msg,
      traceId: trace || undefined,
    })
    isSending.value = false
    isReceiving.value = false
  } finally {
    abortController = null
  }
}

function handleStop(): void {
  abortController?.abort()
}

function handleClear(): void {
  abortController?.abort()
  abortController = null
  messages.value = []
  isSending.value = false
  isReceiving.value = false
}

/** Enter 发送，Shift + Enter 换行 */
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void handleSend()
  }
}

function findAssistant(id: string): ChatMessage | undefined {
  return messages.value.find((m) => m.id === id)
}

function patchAssistant(id: string, patch: Partial<ChatMessage>): void {
  const cur = findAssistant(id)
  if (cur) Object.assign(cur, patch)
}

/** 切换知识库时：abort 当前流 + 清空消息 + 重新生成 session_id */
watch(
  () => props.kbId,
  () => {
    abortController?.abort()
    abortController = null
    messages.value = []
    isSending.value = false
    isReceiving.value = false
    sessionId = genSessionId()
  },
)

onBeforeUnmount(() => {
  abortController?.abort()
  abortController = null
})
</script>

<template>
  <div class="rag-chat">
    <!-- 标题区（仅非 embedded 模式显示） -->
    <div v-if="!embedded" class="rag-chat__head">
      <div class="rag-chat__title-row">
        <MessageSquare :size="18" class="rag-chat__title-icon" />
        <h2 class="rag-chat__title">{{ headerTitle }}</h2>
      </div>
      <p class="rag-chat__desc">{{ headerDesc }}</p>
    </div>

    <!-- 消息区 -->
    <div ref="messagesContainer" class="rag-chat__messages">
      <!-- 空状态 -->
      <div v-if="!hasMessages" class="rag-chat__empty">
        <YuxiEmptyState
          :icon="MessageSquare"
          title="开始一次知识库问答"
          description="输入问题后，RAGAgent 将基于当前知识库生成回答并展示引用来源"
        />
      </div>

      <!-- 消息列表 -->
      <div v-else class="rag-chat__msg-list">
        <ChatMessageBubble
          v-for="msg in messages"
          :key="msg.id"
          :message="msg"
        />
      </div>
    </div>

    <!-- 输入区 -->
    <div class="rag-chat__input-area">
      <Input.TextArea
        v-model:value="question"
        :auto-size="{ minRows: 2, maxRows: 6 }"
        :maxlength="MAX_QUESTION_LEN"
        placeholder="请输入你的问题，Shift + Enter 换行，Enter 发送"
        :disabled="isStreaming"
        class="rag-chat__textarea"
        @keydown="onKeydown"
      />
      <div class="rag-chat__actions">
        <Button
          v-if="!isStreaming"
          type="primary"
          :disabled="!canSend"
          @click="handleSend"
        >
          <template #icon><Send :size="14" /></template>
          发送
        </Button>
        <Button v-else danger @click="handleStop">
          <template #icon><Square :size="14" /></template>
          停止生成
        </Button>
        <Button :disabled="isStreaming || !hasMessages" @click="handleClear">
          <template #icon><RefreshCw :size="14" /></template>
          清空对话
        </Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.rag-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ===== 标题区 ===== */
.rag-chat__head {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 16px;
}

.rag-chat__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rag-chat__title-icon {
  color: var(--yuxi-main-color);
}

.rag-chat__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.rag-chat__desc {
  margin: 0;
  font-size: 13px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
}

/* ===== 消息区 ===== */
.rag-chat__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 4px 4px 16px 0;
}

.rag-chat__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 280px;
}

.rag-chat__msg-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ===== 输入区 ===== */
.rag-chat__input-area {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 0 0;
  border-top: 1px solid var(--yuxi-gray-150);
}

.rag-chat__textarea :deep(textarea) {
  border-radius: var(--yuxi-radius);
  resize: none;
}

.rag-chat__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* ===== 小屏 ===== */
@media (max-width: 575px) {
  .rag-chat__actions {
    flex-wrap: wrap;
  }
}
</style>
