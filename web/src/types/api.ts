/**
 * 后端 API 类型定义（与 docs/FRONTEND_API_CONTRACT.md 对齐）
 * P1.1 仅定义通用响应与 health 相关类型；知识库/文档/聊天类型留待后续批次补齐
 */

/** 统一响应体 */
export interface ApiResponse<T = unknown> {
  /** 0 表示成功；非 0 表示错误（按错误码段位区分异常类型） */
  code: number
  /** 响应消息；错误时为用户可见错误信息，不含堆栈 */
  message: string
  /** 业务数据；错误时为 null */
  data: T | null
  /** 链路追踪 ID */
  trace_id: string
}

/** 分页响应 */
export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 单个组件健康状态 */
export interface ComponentStatus {
  status: 'ok' | 'error'
  latency_ms: number | null
  error: string | null
}

/** 健康检查响应 data */
export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error'
  app: string
  env: string
  timestamp: string
  trace_id: string
  components: {
    postgres: ComponentStatus
    milvus: ComponentStatus
  }
}
