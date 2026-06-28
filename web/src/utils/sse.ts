/**
 * 通用 SSE 事件流解析工具（fetch + ReadableStream）
 *
 * 职责：
 * - 接收 Response.body 的 ReadableStream
 * - 按 text/event-stream 帧边界（\n\n 或 \r\n\r\n）切分
 * - 处理分块不完整情况（缓冲区累积）
 * - 解析每帧的 event / data 字段（兼容多行 data）
 * - 派发 start / delta / done / error 四类业务事件，忽略 ping / 注释 / 非约定事件
 * - 网络中断（reader.read 抛错）抛 NetworkError（中文文案）
 *
 * 不包含业务 UI 逻辑（不持有消息状态、不渲染）。
 */
import { NetworkError } from '@/api/client'

/** 单个 SSE 事件（event + 拼接后的 data） */
export interface SseEvent {
  /** 事件类型，未指定时为 SSE 默认 "message" */
  event: string
  /** data 字段拼接结果（多行 data 以 \n 连接） */
  data: string
}

/** start 事件 payload */
export interface SseStartPayload {
  trace_id: string
}

/** delta 事件 payload */
export interface SseDeltaPayload {
  content: string
}

/** done 事件 payload（retrieval_context 可选，当前后端不下发） */
export interface SseDonePayload {
  trace_id: string
  finish_reason: string
  /** 若后端在 done 事件扩展引用来源，原样透出 */
  retrieval_context?: unknown
}

/** error 事件 payload */
export interface SseErrorPayload {
  trace_id: string
  code: number
  message: string
}

/** SSE 事件回调集合 */
export interface SseHandlers {
  onStart?: (payload: SseStartPayload) => void
  onDelta?: (payload: SseDeltaPayload) => void
  onDone?: (payload: SseDonePayload) => void
  onError?: (payload: SseErrorPayload) => void
}

/** 业务约定的事件类型常量 */
export const SSE_EVENT_START = 'start'
export const SSE_EVENT_DELTA = 'delta'
export const SSE_EVENT_DONE = 'done'
export const SSE_EVENT_ERROR = 'error'

/**
 * 解析单个 SSE 帧（不含尾部 \n\n）
 *
 * 帧格式（SSE 规范）：
 * ```
 * event: xxx
 * data: yyy
 * data: zzz
 * ```
 * - ":" 开头为注释，忽略
 * - 字段名与值之间可选单个空格（按规范剥离）
 * - 多行 data 以 \n 连接
 * - 未出现 event 字段时默认为 "message"
 *
 * @returns 无 data 的帧（纯心跳/注释）返回 null
 */
export function parseSseFrame(frame: string): SseEvent | null {
  let event = 'message'
  const dataLines: string[] = []
  const lines = frame.split('\n')
  for (const raw of lines) {
    const line = raw.replace(/\r$/, '')
    if (line === '') continue // 帧内空行：忽略（帧分隔符已在外层切分）
    if (line.startsWith(':')) continue // 注释行
    const idx = line.indexOf(':')
    const field = idx >= 0 ? line.slice(0, idx) : line
    let value = idx >= 0 ? line.slice(idx + 1) : ''
    if (value.startsWith(' ')) value = value.slice(1) // 剥离单个前导空格
    if (field === 'event') {
      event = value
    } else if (field === 'data') {
      dataLines.push(value)
    }
    // 其他字段（id / retry）忽略
  }
  if (dataLines.length === 0) return null
  return { event, data: dataLines.join('\n') }
}

/**
 * 解析整个 SSE 流
 *
 * - 按 \n\n 或 \r\n\r\n 切分帧
 * - 处理分块不完整（buffer 累积）
 * - 派发给对应 handler
 * - signal abort 时主动 cancel reader 并优雅返回
 * - reader.read 抛错时抛 NetworkError（中文文案）
 *
 * @param body Response.body 的 ReadableStream
 * @param handlers 事件回调
 * @param signal 可选 AbortSignal，用于取消
 * @throws NetworkError 当底层读取失败（且非主动 abort）
 */
export async function parseSseStream(
  body: ReadableStream<Uint8Array>,
  handlers: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''
  let streamEnded = false

  const onAbort = (): void => {
    // 主动取消：尝试 cancel reader，忽略可能的报错
    void reader.cancel().catch(() => {
      /* 已被取消或锁定，忽略 */
    })
  }
  if (signal) {
    if (signal.aborted) {
      onAbort()
      return
    }
    signal.addEventListener('abort', onAbort, { once: true })
  }

  try {
    while (!streamEnded) {
      let chunk: { done: boolean; value?: Uint8Array }
      try {
        chunk = await reader.read()
      } catch {
        if (signal?.aborted) return
        throw new NetworkError('连接后端服务失败，请检查 API 地址或服务状态。')
      }
      if (chunk.done) {
        streamEnded = true
      }
      if (chunk.value) {
        buffer += decoder.decode(chunk.value, { stream: !chunk.done })
        let sepIdx: number
        // 持续切分已完整的帧
        while ((sepIdx = indexOfFrameEnd(buffer)) >= 0) {
          const frameText = buffer.slice(0, sepIdx)
          // 跳过分隔符（\n\n 或 \r\n\r\n）
          const sepLen = buffer.startsWith('\r\n\r\n', sepIdx) ? 4 : 2
          buffer = buffer.slice(sepIdx + sepLen)
          const evt = parseSseFrame(frameText)
          if (evt) dispatchEvent(evt, handlers)
        }
      }
    }
    // 流自然结束：处理 buffer 中残留的最后一片（可能无尾部 \n\n）
    if (buffer.trim()) {
      const evt = parseSseFrame(buffer)
      if (evt) dispatchEvent(evt, handlers)
    }
  } finally {
    if (signal) signal.removeEventListener('abort', onAbort)
    try {
      reader.releaseLock()
    } catch {
      /* 已释放过：忽略 */
    }
  }
}

/** 查找帧结束位置（\n\n 或 \r\n\r\n 最早出现处），未找到返回 -1 */
function indexOfFrameEnd(s: string): number {
  const lf = s.indexOf('\n\n')
  const crlf = s.indexOf('\r\n\r\n')
  if (lf < 0) return crlf
  if (crlf < 0) return lf
  return Math.min(lf, crlf)
}

/** 把单个事件派发到对应 handler */
function dispatchEvent(evt: SseEvent, handlers: SseHandlers): void {
  let payload: Record<string, unknown> = {}
  if (evt.data) {
    try {
      payload = JSON.parse(evt.data) as Record<string, unknown>
    } catch {
      // data 非 JSON：忽略该事件（避免崩溃）
      return
    }
  }
  switch (evt.event) {
    case SSE_EVENT_START:
      handlers.onStart?.({ trace_id: String(payload.trace_id ?? '') })
      break
    case SSE_EVENT_DELTA:
      handlers.onDelta?.({ content: String(payload.content ?? '') })
      break
    case SSE_EVENT_DONE: {
      const done: SseDonePayload = {
        trace_id: String(payload.trace_id ?? ''),
        finish_reason: String(payload.finish_reason ?? 'stop'),
      }
      if (payload.retrieval_context !== undefined) {
        done.retrieval_context = payload.retrieval_context
      }
      handlers.onDone?.(done)
      break
    }
    case SSE_EVENT_ERROR:
      handlers.onError?.({
        trace_id: String(payload.trace_id ?? ''),
        code: Number(payload.code ?? 0),
        message: String(payload.message ?? '生成失败'),
      })
      break
    default:
      // 非约定事件（如 ping / message / 注释）：忽略
      break
  }
}
