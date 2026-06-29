/**
 * API 错误归一化工具（Step 9 收尾）
 *
 * 统一 NetworkError / ApiError / AbortError 的解析，避免在各 UI 页面重复 mapError。
 * - normalizeApiError：通用归一化，返回结构化字段
 * - formatChatStreamError：聊天/检索 SSE 场景的中文文案映射（KbRetrievalTab / RagChatPanel 共用）
 */
import { ApiError, NetworkError } from '@/api/client'

/** 归一化后的错误信息 */
export interface NormalizedApiError {
  /** 中文文案 */
  message: string
  /** 追踪编号（如有） */
  traceId?: string
  /** HTTP 状态码（如有） */
  status?: number
  /** 原始错误对象 */
  raw?: unknown
}

/**
 * 通用错误归一化。
 * - AbortError → "请求已取消"
 * - NetworkError → "无法连接后端服务，请检查 API 地址或服务状态"
 * - ApiError → 后端 message（保留 traceId / httpStatus）
 * - 其他 → "操作失败，请稍后重试"
 */
export function normalizeApiError(err: unknown): NormalizedApiError {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return { message: '请求已取消', raw: err }
  }
  if (err instanceof NetworkError) {
    return { message: '无法连接后端服务，请检查 API 地址或服务状态', raw: err }
  }
  if (err instanceof ApiError) {
    return {
      message: err.message,
      traceId: err.traceId || undefined,
      status: err.httpStatus,
      raw: err,
    }
  }
  return { message: '操作失败，请稍后重试', raw: err }
}

/**
 * 聊天 / 检索 SSE 场景的中文错误文案映射。
 * KbRetrievalTab 与 RagChatPanel 共用，避免重复 mapError。
 *
 * @returns msg 中文文案；trace 追踪编号（如有）
 */
export function formatChatStreamError(err: unknown): { msg: string; trace: string } {
  if (err instanceof DOMException && err.name === 'AbortError') {
    return { msg: '已停止生成', trace: '' }
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
  return { msg: '操作失败，请稍后重试', trace: '' }
}
