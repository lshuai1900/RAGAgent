/**
 * 统一 fetch 封装
 * - API Base URL 从 localStorage 读取（key: ragent.apiBaseUrl），默认 http://localhost:8000
 * - 统一解析 ApiResponse<T>：code===0 返回 data；code!==0 抛 ApiError
 * - 不存储 API Key / 模型密钥
 * - 不直连 PostgreSQL / Milvus / Embedding / LLM
 */
import type { ApiResponse } from '@/types/api'

/** localStorage key：后端 API 地址 */
export const API_BASE_URL_KEY = 'ragent.apiBaseUrl'

/** 默认后端地址 */
export const DEFAULT_API_BASE_URL = 'http://localhost:8000'

/**
 * 读取后端 API Base URL（去尾斜杠）
 * 不存在或非法时返回默认值
 */
export function getApiBaseUrl(): string {
  const raw = localStorage.getItem(API_BASE_URL_KEY)?.trim()
  if (!raw) return DEFAULT_API_BASE_URL
  try {
    // 简单校验：必须是 http/https 开头
    if (!/^https?:\/\//i.test(raw)) return DEFAULT_API_BASE_URL
    return raw.replace(/\/+$/, '')
  } catch {
    return DEFAULT_API_BASE_URL
  }
}

/** 设置后端 API Base URL（写入 localStorage） */
export function setApiBaseUrl(url: string): void {
  const trimmed = url.trim()
  if (trimmed) {
    localStorage.setItem(API_BASE_URL_KEY, trimmed.replace(/\/+$/, ''))
  } else {
    localStorage.removeItem(API_BASE_URL_KEY)
  }
}

/** API 错误：含中文 message 与追踪编号 */
export class ApiError extends Error {
  /** 后端错误码 */
  code: number
  /** 追踪编号 */
  traceId: string
  /** HTTP 状态码 */
  httpStatus: number

  constructor(message: string, code: number, traceId: string, httpStatus: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.traceId = traceId
    this.httpStatus = httpStatus
  }
}

/** 网络错误：无法连接后端 */
export class NetworkError extends Error {
  constructor(message = '连接后端失败，请检查 API 地址设置') {
    super(message)
    this.name = 'NetworkError'
  }
}

/** 通用请求选项 */
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  /** JSON 请求体（自动序列化） */
  body?: unknown
  /** 自定义请求头 */
  headers?: Record<string, string>
  /** 查询参数 */
  query?: Record<string, string | number | boolean | undefined | null>
  /** AbortSignal，用于取消请求 */
  signal?: AbortSignal
}

/** 拼接 URL 与 query */
function buildUrl(path: string, query?: RequestOptions['query']): string {
  const base = getApiBaseUrl()
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') {
      params.append(key, String(value))
    }
  }
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

/**
 * 统一请求函数（返回 data 部分）
 * @throws ApiError 当 code !== 0 或 HTTP 非 2xx
 * @throws NetworkError 当 fetch 本身失败（无法连接）
 */
export async function request<T = unknown>(
  path: string,
  options?: RequestOptions,
): Promise<T>
/** 统一请求函数（raw=true 时返回完整 ApiResponse） */
export async function request<T = unknown>(
  path: string,
  options: RequestOptions & { raw: true },
): Promise<ApiResponse<T>>
export async function request<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T | ApiResponse<T>> {
  const { method = 'GET', body, headers = {}, query, signal } = options
  const raw = (options as { raw?: boolean }).raw === true

  const url = buildUrl(path, query)
  const finalHeaders: Record<string, string> = { ...headers }
  let reqBody: BodyInit | undefined
  if (body !== undefined) {
    finalHeaders['Content-Type'] = finalHeaders['Content-Type'] ?? 'application/json'
    reqBody = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers: finalHeaders,
      body: reqBody,
      signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new NetworkError()
  }

  // 尝试解析 body 为 ApiResponse（后端 2xx/4xx/5xx 均返回此结构）
  let payload: ApiResponse<T> | null = null
  const text = await response.text()
  if (text) {
    try {
      payload = JSON.parse(text) as ApiResponse<T>
    } catch {
      payload = null
    }
  }

  // HTTP 非 2xx：尝试从 payload 取 code/message/trace_id，否则用通用中文文案
  if (!response.ok) {
    const message = payload?.message || httpStatusToMessage(response.status)
    const code = payload?.code ?? response.status
    const traceId = payload?.trace_id ?? ''
    throw new ApiError(message, code, traceId, response.status)
  }

  // HTTP 2xx 但 code !== 0
  if (!payload) {
    throw new ApiError('响应格式错误', response.status, '', response.status)
  }
  if (payload.code !== 0) {
    throw new ApiError(payload.message || '请求失败', payload.code, payload.trace_id, response.status)
  }

  return (raw ? payload : payload.data) as T | ApiResponse<T>
}

/** HTTP 状态码到中文文案兜底 */
function httpStatusToMessage(status: number): string {
  if (status === 400) return '请求参数有误'
  if (status === 401) return '未授权'
  if (status === 403) return '禁止访问'
  if (status === 404) return '资源不存在'
  if (status === 422) return '请求参数有误'
  if (status >= 500) return '服务暂不可用'
  return `请求失败（HTTP ${status}）`
}

/**
 * 构造错误展示文案（中文 message + 追踪编号）
 */
export function formatApiError(err: unknown): string {
  if (err instanceof NetworkError) {
    return err.message
  }
  if (err instanceof ApiError) {
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  if (err instanceof DOMException && err.name === 'AbortError') {
    return '请求已取消'
  }
  return '操作失败，请稍后重试'
}
