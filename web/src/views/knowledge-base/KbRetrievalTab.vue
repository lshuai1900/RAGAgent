<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 7：Yuxi 风格检索测试页，左右分栏 + 本地 SSE + citations→references 映射。
-->
<script setup lang="ts">
/**
 * 知识库详情页 - 检索测试 Tab（Step 7 / Yuxi 风格）
 *
 * - 左右分栏：左侧查询输入，右侧结果展示（小屏上下堆叠）
 * - 直接调用 streamChatSse（fetch + ReadableStream），不共享 chat store（避免与 Chat Tab 互相污染）
 * - AbortController 支持停止生成与离开页面中断
 * - done 事件的 citations / references / retrieval_context 统一映射为 UiChatReference[]
 * - 不引入 Markdown 渲染；answer 用 pre-wrap 展示
 * - 不实现会话历史；session_id 每次检索临时生成
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Button, Input, message } from 'ant-design-vue'
import {
  AlertCircle,
  FileText,
  Loader,
  RefreshCw,
  Search,
  Square,
} from 'lucide-vue-next'
import { streamChatSse } from '@/api/chat'
import { ApiError, NetworkError, formatApiError } from '@/api/client'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import YuxiCard from '@/components/yuxi/YuxiCard.vue'
import YuxiEmptyState from '@/components/yuxi/YuxiEmptyState.vue'
import SourceReferenceCard from '@/components/chat/SourceReferenceCard.vue'
import { mapCitationsToReferences, type UiChatReference } from '@/utils/chatReferences'
import type { ChatSseRequest } from '@/types/api'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId ?? ''))

const kbStore = useKnowledgeBaseStore()
const { detail } = storeToRefs(kbStore)

/** 问题最大长度 */
const MAX_QUESTION_LEN = 2000
/** 默认 top_k */
const DEFAULT_TOP_K = 5

type Phase = 'idle' | 'sending' | 'receiving' | 'done' | 'error'

const question = ref('')
const answer = ref('')
const phase = ref<Phase>('idle')
const traceId = ref('')
const finishReason = ref('')
const references = ref<UiChatReference[]>([])
const errorMsg = ref('')

let abortController: AbortController | null = null

const isStreaming = computed(
  () => phase.value === 'sending' || phase.value === 'receiving',
)

const canSend = computed(
  () => !isStreaming.value && question.value.trim().length > 0,
)

/** 是否有结果可展示（answer 非空或 done/error） */
const hasResult = computed(
  () => answer.value.length > 0 || phase.value === 'done' || phase.value === 'error',
)

/** 阶段文案 */
const phaseText = computed(() => {
  switch (phase.value) {
    case 'sending':
      return '正在建立连接'
    case 'receiving':
      return '正在生成回答'
    case 'done':
      return '生成完成'
    case 'error':
      return '生成失败'
    default:
      return ''
  }
})

/** 生成临时 session_id（不保存到会话历史） */
function genSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `ragagent-retrieval-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 错误映射（中文） */
function mapError(err: unknown): { msg: string; trace: string } {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return { msg: '已停止生成', trace: traceId.value }
  }
  if (err instanceof NetworkError) {
    return { msg: '无法连接后端服务，请检查 API 地址或服务状态', trace: '' }
  }
  if (err instanceof ApiError) {
    const trace = err.traceId
    if (err.httpStatus === 400 || err.httpStatus === 422) {
      return { msg: '请求参数不正确，请检查问题内容后重试', trace }
    }
    if (err.httpStatus === 404) {
      return { msg: '知识库不存在或已被删除', trace }
    }
    if (err.httpStatus === 409) {
      return { msg: '当前知识库正在处理中，请稍后重试', trace }
    }
    if (err.httpStatus >= 500) {
      return { msg: '服务器内部错误，请稍后重试', trace }
    }
    return { msg: err.message, trace }
  }
  return { msg: formatApiError(err), trace: '' }
}

/** SSE error 事件错误映射 */
function mapSseError(data: { message: string; trace_id: string; code: number }): string {
  // 后端 error 事件已有中文 message 时直接用
  return data.message || '生成失败'
}

async function handleSend(): Promise<void> {
  const q = question.value.trim()
  if (!q) {
    message.warning('请输入问题')
    return
  }
  if (!kbId.value) {
    message.error('缺少知识库编号')
    return
  }
  if (isStreaming.value) return

  // 重置状态
  answer.value = ''
  traceId.value = ''
  finishReason.value = ''
  references.value = []
  errorMsg.value = ''
  phase.value = 'sending'

  const payload: ChatSseRequest = {
    session_id: genSessionId(),
    kb_id: kbId.value,
    question: q,
    top_k: DEFAULT_TOP_K,
  }

  abortController?.abort()
  abortController = new AbortController()

  /** 是否已收到终态事件（done / error），用于检测流中断 */
  let receivedTerminal = false

  try {
    await streamChatSse(
      payload,
      {
        onStart: (data) => {
          phase.value = 'receiving'
          traceId.value = data.trace_id
        },
        onDelta: (data) => {
          phase.value = 'receiving'
          answer.value += data.content
        },
        onDone: (data) => {
          if (data.trace_id) traceId.value = data.trace_id
          finishReason.value = data.finish_reason || ''
          references.value = mapCitationsToReferences(data)
          phase.value = 'done'
          receivedTerminal = true
        },
        onError: (data) => {
          traceId.value = data.trace_id || traceId.value
          errorMsg.value = mapSseError(data)
          phase.value = 'error'
          receivedTerminal = true
        },
      },
      abortController.signal,
    )

    // 流正常结束但未收到 done / error：视为中断
    if (!receivedTerminal) {
      errorMsg.value = '流式响应解析失败，请稍后重试'
      phase.value = 'error'
    }
  } catch (err) {
    const { msg, trace } = mapError(err)
    errorMsg.value = msg
    if (trace && !traceId.value) traceId.value = trace
    // AbortError 不视为红色错误（已停止生成）
    if (err instanceof DOMException && err.name === 'AbortError') {
      phase.value = 'done'
    } else {
      phase.value = 'error'
    }
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
  question.value = ''
  answer.value = ''
  traceId.value = ''
  finishReason.value = ''
  references.value = []
  errorMsg.value = ''
  phase.value = 'idle'
}

/** Enter 发送，Shift + Enter 换行 */
function onKeydown(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    void handleSend()
  }
}

onBeforeUnmount(() => {
  // 离开页面中断进行中的 SSE，避免内存泄漏与旧流污染
  abortController?.abort()
  abortController = null
})
</script>

<template>
  <div class="retrieval-test">
    <!-- 左侧：查询输入区 -->
    <section class="retrieval-test__query">
      <div class="retrieval-test__query-head">
        <div class="retrieval-test__title-row">
          <Search :size="18" class="retrieval-test__title-icon" />
          <h2 class="retrieval-test__title">检索测试</h2>
        </div>
        <p class="retrieval-test__desc">
          输入问题，测试当前知识库的 RAG 检索与回答效果<span v-if="detail?.name">：{{ detail.name }}</span>
        </p>
      </div>

      <YuxiCard class="retrieval-test__input-card">
        <Input.TextArea
          v-model:value="question"
          :auto-size="{ minRows: 4, maxRows: 10 }"
          :maxlength="MAX_QUESTION_LEN"
          :placeholder="'请输入要测试的问题，例如：这个知识库主要讲了什么？'"
          :disabled="isStreaming"
          class="retrieval-test__textarea"
          @keydown="onKeydown"
        />
        <div class="retrieval-test__actions">
          <Button
            v-if="!isStreaming"
            type="primary"
            :disabled="!canSend"
            @click="handleSend"
          >
            <template #icon><Search :size="14" /></template>
            开始检索
          </Button>
          <Button v-else danger @click="handleStop">
            <template #icon><Square :size="14" /></template>
            停止生成
          </Button>
          <Button :disabled="isStreaming" @click="handleClear">
            <template #icon><RefreshCw :size="14" /></template>
            清空
          </Button>
        </div>
        <p class="retrieval-test__hint">Enter 检索，Shift + Enter 换行</p>
      </YuxiCard>
    </section>

    <!-- 右侧：结果展示区 -->
    <section class="retrieval-test__result">
      <!-- 空状态 -->
      <YuxiCard
        v-if="!hasResult && phase !== 'error'"
        :flat="true"
        class="retrieval-test__result-empty"
      >
        <YuxiEmptyState
          :icon="Search"
          title="等待检索"
          description="输入问题后，将在这里显示检索回答和引用来源"
          full-height
        />
      </YuxiCard>

      <!-- 结果内容 -->
      <div v-else class="retrieval-test__result-body">
        <!-- 回答区 -->
        <YuxiCard title="检索回答" class="retrieval-test__answer-card">
          <template #extra>
            <span v-if="phaseText" class="retrieval-test__phase">
              <Loader
                v-if="isStreaming"
                :size="12"
                class="retrieval-test__spin"
              />
              {{ phaseText }}
            </span>
          </template>

          <div v-if="!answer && isStreaming" class="retrieval-test__thinking">
            正在生成回答…
          </div>
          <pre v-else class="retrieval-test__answer">{{ answer }}</pre>

          <!-- 错误提示（保留已有回答） -->
          <div
            v-if="phase === 'error' && errorMsg"
            class="retrieval-test__error"
          >
            <AlertCircle :size="14" />
            <span>{{ errorMsg }}</span>
          </div>
        </YuxiCard>

        <!-- 元信息：trace_id / finish_reason -->
        <YuxiCard v-if="traceId || finishReason" class="retrieval-test__meta-card">
          <div class="retrieval-test__meta">
            <div v-if="traceId" class="retrieval-test__meta-item">
              <span class="retrieval-test__meta-label">追踪编号</span>
              <span class="retrieval-test__meta-value">{{ traceId }}</span>
            </div>
            <div v-if="finishReason" class="retrieval-test__meta-item">
              <span class="retrieval-test__meta-label">结束原因</span>
              <span class="retrieval-test__meta-value">{{ finishReason }}</span>
            </div>
          </div>
        </YuxiCard>

        <!-- 引用来源 -->
        <YuxiCard title="引用来源" class="retrieval-test__sources-card">
          <div v-if="references.length === 0" class="retrieval-test__no-sources">
            <FileText :size="20" class="retrieval-test__no-sources-icon" />
            <span>暂无引用来源</span>
          </div>
          <div v-else class="retrieval-test__sources-list">
            <SourceReferenceCard
              v-for="(ref, idx) in references"
              :key="idx"
              :reference="ref"
              :index="idx + 1"
            />
          </div>
        </YuxiCard>
      </div>
    </section>
  </div>
</template>

<style scoped>
.retrieval-test {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 16px;
  align-items: start;
}

/* ===== 左侧查询区 ===== */
.retrieval-test__query {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 16px;
}

.retrieval-test__query-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.retrieval-test__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.retrieval-test__title-icon {
  color: var(--yuxi-main-color);
}

.retrieval-test__title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.retrieval-test__desc {
  margin: 0;
  font-size: 13px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
}

.retrieval-test__input-card :deep(.yuxi-card__body) {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.retrieval-test__textarea :deep(textarea) {
  border-radius: var(--yuxi-radius-sm);
  resize: none;
}

.retrieval-test__actions {
  display: flex;
  gap: 8px;
}

.retrieval-test__hint {
  margin: 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

/* ===== 右侧结果区 ===== */
.retrieval-test__result {
  min-width: 0;
}

.retrieval-test__result-empty :deep(.yuxi-card__body) {
  min-height: 320px;
}

.retrieval-test__result-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.retrieval-test__answer-card :deep(.yuxi-card__header) {
  border-bottom: 1px solid var(--yuxi-gray-150);
  padding-bottom: 10px;
  margin-bottom: 10px;
}

.retrieval-test__phase {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--yuxi-main-600);
  font-weight: 500;
}

.retrieval-test__spin {
  animation: retrieval-spin 1s linear infinite;
}

@keyframes retrieval-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.retrieval-test__thinking {
  color: var(--yuxi-gray-500);
  font-style: italic;
  font-size: 14px;
}

.retrieval-test__answer {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
  color: var(--yuxi-gray-800);
}

.retrieval-test__error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: var(--yuxi-radius-sm);
  background: var(--yuxi-error-50);
  border: 1px solid var(--yuxi-error-500);
  color: var(--yuxi-error-700);
  font-size: 13px;
  line-height: 1.5;
}

/* ===== 元信息 ===== */
.retrieval-test__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.retrieval-test__meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.retrieval-test__meta-label {
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.retrieval-test__meta-value {
  font-size: 13px;
  color: var(--yuxi-gray-700);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
}

/* ===== 引用来源 ===== */
.retrieval-test__no-sources {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--yuxi-gray-400);
  font-size: 13px;
}

.retrieval-test__no-sources-icon {
  opacity: 0.6;
}

.retrieval-test__sources-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ===== 小屏：上下堆叠 ===== */
@media (max-width: 991px) {
  .retrieval-test {
    grid-template-columns: 1fr;
  }

  .retrieval-test__query {
    position: static;
  }
}
</style>
