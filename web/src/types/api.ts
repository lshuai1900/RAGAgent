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

// ===== 知识库（与 docs/FRONTEND_API_CONTRACT.md 3.2-3.4 对齐）=====

/** 创建知识库请求体 */
export interface KnowledgeBaseCreate {
  name: string
  description?: string | null
  embedding_model?: string
  embedding_dim?: number
  chunk_strategy?: 'fixed' | 'sentence' | 'recursive'
  chunk_size?: number
  chunk_overlap?: number
}

/** 知识库响应 */
export interface KnowledgeBaseOut {
  id: string
  name: string
  description: string | null
  collection_name: string
  embedding_dim: number
  embedding_model: string
  chunk_strategy: string
  chunk_size: number
  chunk_overlap: number
  document_count: number
  status: string
  created_at: string
  updated_at: string
}

/** 知识库分页响应 data */
export interface KnowledgeBasePage extends PageResponse<KnowledgeBaseOut> {}

// ===== 文档（与 docs/FRONTEND_API_CONTRACT.md 3.5-3.7 对齐）=====

/** 文档响应 */
export interface DocumentOut {
  id: string
  kb_id: string
  name: string
  file_type: string
  file_size: number
  file_hash: string
  status: string
  chunk_count: number
  total_tokens: number
  error_message: string | null
  created_at: string
  updated_at: string
}

/** 文档上传响应 */
export interface DocumentUploadResponse {
  document_id: string
  kb_id: string
  name: string
  file_type: string
  file_size: number
  file_hash: string
  status: string
  duplicated: boolean
}

/** 文档分页响应 data */
export interface DocumentPage extends PageResponse<DocumentOut> {}

