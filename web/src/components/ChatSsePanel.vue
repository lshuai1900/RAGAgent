<script setup lang="ts">
/**
 * 知识库详情页"聊天问答"标签页主面板（P1.4-A）
 *
 * - 基于 POST /api/v1/chat/sse 流式问答
 * - fetch + ReadableStream（禁用 EventSource）
 * - 状态：sending（开始生成）→ receiving（生成中）→ done / error
 * - 展示 trace_id（追踪编号）与 retrieval_context（引用来源）
 * - Enter 发送，Shift + Enter 换行
 * - 发送中输入框 + 发送按钮禁用，避免重复发送
 * - 组件卸载时 abort 进行中的 SSE 请求
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { Alert, Button, Card, Empty, Input, Tag, message } from 'ant-design-vue'
import {
  AlertCircle,
  Bot,
  Loader,
  RefreshCw,
  Send,
  Square,
  User,
} from 'lucide-vue-next'
import { useChatStore } from '@/stores/chat'
import RetrievalContextPanel from '@/components/RetrievalContextPanel.vue'
import type { ChatMessage } from '@/types/api'

interface Props {
  /** 当前知识库 ID */
  kbId: string
  /** 当前知识库名称（用于顶部说明展示） */
  kbName?: string
}
const props = defineProps<Props>()

const chatStore = useChatStore()
const { messages, state, error, isStreaming } = storeToRefs(chatStore)

const question = ref<string>('')

const canSend = computed(
  () => !isStreaming.value && question.value.trim().length > 0,
)

/** 最新一条助手消息（用于展示追踪编号与引用来源） */
const lastAssistant = computed<ChatMessage | null>(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i].role === 'assistant') return messages.value[i]
  }
  return null
})

/** 是否已结束（done / error） */
const isFinished = computed(
  () => state.value === 'done' || state.value === 'error',
)

/** 顶部阶段文案 */
const phaseText = computed<string>(() => {
  switch (state.value) {
    case 'sending':
      return '开始生成'
    case 'receiving':
      return '生成中'
    case 'done':
      return '生成完成'
    case 'error':
      return '生成失败'
    default:
      return ''
  }
})

/** 顶部阶段 Tag 颜色 */
const phaseColor = computed<string>(() => {
  switch (state.value) {
    case 'sending':
    case 'receiving':
      return 'processing'
    case 'done':
      return 'success'
    case 'error':
      return 'error'
    default:
      return 'default'
  }
})

/** 助手消息的状态 Tag 信息 */
function statusTagFor(
  msg: ChatMessage,
): { text: string; color: string } | null {
  if (msg.role === 'user') return null
  switch (msg.status) {
    case 'sending':
      return { text: '开始生成', color: 'processing' }
    case 'receiving':
      return { text: '生成中', color: 'processing' }
    case 'done':
      return { text: '生成完成', color: 'success' }
    case 'error':
      return { text: '生成失败', color: 'error' }
    default:
      return null
  }
}

function handleSend(): void {
  const q = question.value.trim()
  if (!q) {
    message.warning('请输入问题。')
    return
  }
  if (!props.kbId) {
    message.error('缺少知识库编号。')
    return
  }
  if (isStreaming.value) return
  question.value = ''
  // store 内部已捕获所有错误并写入 state.error，这里只兜底意外抛出
  void chatStore.send(props.kbId, q).catch(() => {
    /* 已在 store 中处理 */
  })
}

function handleStop(): void {
  chatStore.abort()
}

function handleClear(): void {
  chatStore.reset()
}

/** Enter 发送，Shift + Enter 换行；输入法组合态不触发 */
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    handleSend()
  }
}

onBeforeUnmount(() => {
  // 卸载时取消进行中的 SSE 请求，避免内存泄漏
  chatStore.abort()
})
</script>

<template>
  <div class="chat-sse-panel">
    <!-- 顶部说明 -->
    <div class="chat-sse-panel__head">
      <div class="chat-sse-panel__title">
        <Bot :size="16" class="chat-sse-panel__icon" />
        <span>聊天问答</span>
      </div>
      <p class="chat-sse-panel__desc">
        基于当前知识库进行流式问答<span v-if="kbName">：{{ kbName }}</span>
      </p>
    </div>

    <!-- 输入区 -->
    <Card :bordered="true" size="small" class="chat-sse-panel__input-card">
      <div class="chat-sse-panel__input-row">
        <Input.TextArea
          v-model:value="question"
          :auto-size="{ minRows: 2, maxRows: 6 }"
          placeholder="请输入你的问题"
          :disabled="isStreaming"
          class="chat-sse-panel__input"
          @keydown="onKeydown"
        />
        <div class="chat-sse-panel__btns">
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
            停止
          </Button>
          <Button :disabled="isStreaming" @click="handleClear">
            <template #icon><RefreshCw :size="14" /></template>
            清空对话
          </Button>
        </div>
      </div>
      <p class="chat-sse-panel__hint">Enter 发送，Shift + Enter 换行</p>
    </Card>

    <!-- 错误提示（来自 store 顶层错误，例如网络中断、未输入问题） -->
    <Alert
      v-if="error && state === 'error'"
      type="error"
      show-icon
      :message="error"
    />

    <!-- 回答区 -->
    <Card :bordered="true" size="small" class="chat-sse-panel__answer-card">
      <template #title>
        <div class="chat-sse-panel__answer-head">
          <span>回答内容</span>
          <Tag v-if="phaseText" :color="phaseColor">
            <template v-if="state === 'sending' || state === 'receiving'">
              <Loader :size="11" class="chat-sse-panel__spin" />
            </template>
            {{ phaseText }}
          </Tag>
        </div>
      </template>

      <div v-if="messages.length === 0" class="chat-sse-panel__empty">
        <Empty
          :image="Empty.PRESENTED_IMAGE_SIMPLE"
          description="暂无对话记录，输入问题开始提问"
        />
      </div>

      <div v-else class="chat-sse-panel__messages">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="chat-msg"
          :class="`chat-msg--${msg.role}`"
        >
          <div class="chat-msg__avatar">
            <component :is="msg.role === 'user' ? User : Bot" :size="14" />
          </div>
          <div class="chat-msg__body">
            <div class="chat-msg__meta">
              <span class="chat-msg__role">
                {{ msg.role === 'user' ? '用户' : '助手' }}
              </span>
              <Tag
                v-if="statusTagFor(msg)"
                :color="statusTagFor(msg)!.color"
                class="chat-msg__status"
              >
                <template v-if="msg.status === 'sending' || msg.status === 'receiving'">
                  <Loader :size="11" class="chat-sse-panel__spin" />
                </template>
                {{ statusTagFor(msg)!.text }}
              </Tag>
            </div>
            <div class="chat-msg__content">
              <template v-if="msg.role === 'assistant' && msg.status === 'sending' && !msg.content">
                <span class="chat-msg__thinking">正在生成回答...</span>
              </template>
              <template v-else>
                <pre class="chat-msg__pre">{{ msg.content }}</pre>
              </template>
            </div>
            <div
              v-if="msg.role === 'assistant' && msg.status === 'error' && msg.error_message"
              class="chat-msg__error"
            >
              <AlertCircle :size="12" />
              <span>{{ msg.error_message }}</span>
            </div>
          </div>
        </div>
      </div>
    </Card>

    <!-- 追踪编号 -->
    <Card
      v-if="lastAssistant && lastAssistant.trace_id"
      :bordered="true"
      size="small"
      class="chat-sse-panel__trace-card"
    >
      <div class="chat-sse-panel__trace">
        <span class="chat-sse-panel__trace-label">追踪编号：</span>
        <span class="chat-sse-panel__trace-value">{{ lastAssistant.trace_id }}</span>
      </div>
    </Card>

    <!-- 引用来源（done / error 后展示；后端不下发时显示"暂无引用来源"） -->
    <RetrievalContextPanel
      v-if="lastAssistant && (lastAssistant.status === 'done' || lastAssistant.status === 'error') && isFinished"
      :items="lastAssistant.retrieval_context"
    />
  </div>
</template>

<style scoped>
.chat-sse-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-sse-panel__head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-sse-panel__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
}

.chat-sse-panel__icon {
  color: #1677ff;
}

.chat-sse-panel__desc {
  margin: 0;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.chat-sse-panel__input-card,
.chat-sse-panel__answer-card,
.chat-sse-panel__trace-card {
  border-radius: var(--app-radius);
}

.chat-sse-panel__input-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.chat-sse-panel__input {
  flex: 1;
}

.chat-sse-panel__btns {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-sse-panel__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--app-text-tertiary);
}

.chat-sse-panel__answer-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.chat-sse-panel__empty {
  padding: 24px 0;
  display: flex;
  justify-content: center;
}

.chat-sse-panel__messages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 4px;
}

.chat-sse-panel__spin {
  animation: chat-sse-panel-spin 1s linear infinite;
  display: inline-block;
}

@keyframes chat-sse-panel-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.chat-msg {
  display: flex;
  gap: 10px;
}

.chat-msg__avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f5ff;
  color: #1677ff;
  flex-shrink: 0;
}

.chat-msg--assistant .chat-msg__avatar {
  background-color: #f6ffed;
  color: #52c41a;
}

.chat-msg__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-msg__meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--app-text-tertiary);
}

.chat-msg__role {
  font-weight: 500;
}

.chat-msg__status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.chat-msg__content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--app-text);
}

.chat-msg__pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
}

.chat-msg__thinking {
  color: var(--app-text-tertiary);
  font-style: italic;
}

.chat-msg__error {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #cf1322;
  font-size: 13px;
}

.chat-sse-panel__trace {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.chat-sse-panel__trace-label {
  color: var(--app-text-tertiary);
}

.chat-sse-panel__trace-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--app-text-secondary);
  font-size: 12px;
}
</style>
