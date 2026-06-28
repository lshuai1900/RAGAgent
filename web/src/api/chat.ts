/**
 * 聊天 SSE 客户端
 *
 * 对应后端：
 * - POST /api/v1/chat/sse（流式问答，返回 text/event-stream）
 *
 * 硬约束：
 * - 必须用 fetch + ReadableStream，禁用 EventSource（EventSource 仅支持 GET）
 * - SSE 不走 ApiResponse 包装，单独解析 start / delta / done / error 四类事件
 * - HTTP 非 2xx 时后端可能返回 ApiResponse 错误体，需解析出 message / trace_id
 */
import { ApiError, NetworkError, getApiBaseUrl } from './client'
import { parseSseStream, type SseHandlers } from '@/utils/sse'
import type { ChatSseRequest } from '@/types/api'

/** 网络中断 / 连接后端失败的中文文案 */
const NETWORK_ERROR_MESSAGE = '连接后端服务失败，请检查 API 地址或服务状态。'

/**
 * 发起 SSE 流式问答
 *
 * - 拿到 Response 后取 body.getReader()，由 parseSseStream 派发事件
 * - HTTP 非 2xx：尝试从 body 解析 ApiResponse 错误体，抛 ApiError
 * - fetch 本身失败：抛 NetworkError
 * - 流解析过程中的网络中断：由 parseSseStream 抛 NetworkError
 *
 * @param payload 请求体（session_id / kb_id / question / top_k 等）
 * @param handlers 事件回调集合
 * @param signal 可选 AbortSignal，用于组件卸载或用户主动停止
 */
export async function streamChatSse(
  payload: ChatSseRequest,
  handlers: SseHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const url = `${getApiBaseUrl()}/api/v1/chat/sse`

  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new NetworkError(NETWORK_ERROR_MESSAGE)
  }

  // HTTP 非 2xx：后端可能返回 ApiResponse 错误体
  if (!response.ok) {
    let errMsg = '生成失败'
    let traceId = ''
    let code = response.status
    try {
      const text = await response.text()
      if (text) {
        const body = JSON.parse(text) as {
          code?: number
          message?: string
          trace_id?: string
        }
        errMsg = body.message || errMsg
        traceId = body.trace_id || ''
        code = body.code ?? code
      }
    } catch {
      // body 解析失败：用 HTTP 兜底文案
      errMsg = httpStatusToMessage(response.status)
    }
    throw new ApiError(errMsg, code, traceId, response.status)
  }

  if (!response.body) {
    throw new NetworkError('后端未返回事件流，请稍后重试。')
  }

  await parseSseStream(response.body, handlers, signal)
}

/** HTTP 状态码到中文文案兜底 */
function httpStatusToMessage(status: number): string {
  if (status === 400 || status === 422) return '请求参数有误'
  if (status === 401) return '未授权'
  if (status === 403) return '禁止访问'
  if (status === 404) return '接口不存在'
  if (status >= 500) return '服务暂不可用'
  return `生成失败（HTTP ${status}）`
}
