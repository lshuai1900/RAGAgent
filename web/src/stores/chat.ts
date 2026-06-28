/**
 * 聊天 Pinia store
 *
 * 职责：
 * - 单知识库单会话 SSE 流式问答（P1.4-A）
 * - 不直接发 fetch，统一调 api/chat.ts
 * - 发送中禁用重复发送
 * - 组件卸载或用户主动停止时 abort 进行中的请求
 * - 流自然结束但未收到 done / error 时视为中断，提示"回答中断，请重试"
 *
 * 不在本轮实现：多会话管理、会话列表、历史会话切换、对话标题生成
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { streamChatSse as apiStreamChatSse } from '@/api/chat'
import { ApiError, formatApiError } from '@/api/client'
import type {
  ChatMessage,
  ChatSseRequest,
  RetrievalContextItem,
} from '@/types/api'

export type ChatState =
  | 'idle'
  | 'sending' // 已发送，等待 start
  | 'receiving' // 收到 start / delta，等待 done
  | 'done'
  | 'error'

/** 默认 top_k */
const DEFAULT_TOP_K = 5

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const state = ref<ChatState>('idle')
  const error = ref<string>('')
  const currentKbId = ref<string>('')
  const sessionId = ref<string>('')

  let abortController: AbortController | null = null

  const isStreaming = computed(
    () => state.value === 'sending' || state.value === 'receiving',
  )

  /** 获取或新建 session_id（同一会话内复用） */
  function ensureSessionId(): string {
    if (!sessionId.value) {
      sessionId.value = createSessionId()
    }
    return sessionId.value
  }

  /** 重置 session_id（"新建对话"场景，本轮不暴露按钮，预留方法） */
  function resetSession(): void {
    sessionId.value = createSessionId()
  }

  /** 重置整个 store（切换知识库 / 离开详情页时调用） */
  function reset(): void {
    abortController?.abort()
    abortController = null
    messages.value = []
    state.value = 'idle'
    error.value = ''
    currentKbId.value = ''
    sessionId.value = ''
  }

  /** 用户主动停止 */
  function abort(): void {
    abortController?.abort()
  }

  /**
   * 发送问题并流式接收回答
   *
   * @throws 不抛错（错误写入 state.error 与助手消息 error_message）
   */
  async function send(
    kbId: string,
    question: string,
    opts?: { top_k?: number },
  ): Promise<void> {
    const q = question.trim()
    if (!q) {
      state.value = 'error'
      error.value = '请输入问题。'
      return
    }
    if (!kbId) {
      state.value = 'error'
      error.value = '缺少知识库编号。'
      return
    }
    if (isStreaming.value) return // 防止重复发送

    currentKbId.value = kbId
    error.value = ''
    state.value = 'sending'

    // 1. 追加用户消息（已完成态）
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content: q,
      status: 'done',
      trace_id: '',
      error_message: '',
      retrieval_context: null,
      created_at: nowIso(),
    }
    messages.value.push(userMsg)

    // 2. 追加助手占位消息（sending 态）
    const assistantId = genId()
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      status: 'sending',
      trace_id: '',
      error_message: '',
      retrieval_context: null,
      created_at: nowIso(),
    }
    messages.value.push(assistantMsg)

    const payload: ChatSseRequest = {
      session_id: ensureSessionId(),
      kb_id: kbId,
      question: q,
      top_k: opts?.top_k ?? DEFAULT_TOP_K,
    }

    abortController?.abort()
    abortController = new AbortController()

    try {
      await apiStreamChatSse(
        payload,
        {
          onStart: (data) => {
            state.value = 'receiving'
            patchAssistant(assistantId, {
              trace_id: data.trace_id,
              status: 'receiving',
            })
          },
          onDelta: (data) => {
            state.value = 'receiving'
            const cur = findAssistant(assistantId)
            if (cur) {
              cur.content += data.content
              cur.status = 'receiving'
            }
          },
          onDone: (data) => {
            const cur = findAssistant(assistantId)
            if (cur) {
              if (data.trace_id) cur.trace_id = data.trace_id
              cur.status = 'done'
              if (Array.isArray(data.retrieval_context)) {
                cur.retrieval_context =
                  data.retrieval_context as RetrievalContextItem[]
              }
            }
            state.value = 'done'
          },
          onError: (data) => {
            const cur = findAssistant(assistantId)
            if (cur) {
              if (data.trace_id) cur.trace_id = data.trace_id
              cur.error_message = data.message || '生成失败'
              cur.status = 'error'
            }
            state.value = 'error'
            error.value = data.message || '生成失败'
          },
        },
        abortController.signal,
      )

      // 流正常结束但未收到 done / error：视为中断
      const cur = findAssistant(assistantId)
      if (cur && cur.status !== 'done' && cur.status !== 'error') {
        cur.status = 'error'
        cur.error_message = '回答中断，请重试。'
        state.value = 'error'
        error.value = '回答中断，请重试。'
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 主动取消：不当作错误，恢复 idle
        const cur = findAssistant(assistantId)
        if (cur && cur.status !== 'done' && cur.status !== 'error') {
          cur.status = 'error'
          cur.error_message = '已取消'
        }
        state.value = 'idle'
        return
      }
      const msg = formatApiError(err)
      const cur = findAssistant(assistantId)
      if (cur) {
        cur.status = 'error'
        cur.error_message = msg
        if (err instanceof ApiError) cur.trace_id = err.traceId
      }
      state.value = 'error'
      error.value = msg
    } finally {
      abortController = null
    }
  }

  function findAssistant(id: string): ChatMessage | undefined {
    return messages.value.find((m) => m.id === id)
  }

  function patchAssistant(id: string, patch: Partial<ChatMessage>): void {
    const cur = findAssistant(id)
    if (cur) Object.assign(cur, patch)
  }

  return {
    // 状态
    messages,
    state,
    error,
    currentKbId,
    sessionId,
    isStreaming,
    // 操作
    send,
    abort,
    reset,
    resetSession,
  }
})

/** 生成会话 ID（优先 crypto.randomUUID） */
function createSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 生成消息主键 */
function genId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 当前 ISO 时间 */
function nowIso(): string {
  return new Date().toISOString()
}
