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

// ===== 聊天（与 docs/FRONTEND_API_CONTRACT.md 3.8 对齐）=====

/** SSE 流式问答请求体 */
export interface ChatSseRequest {
  /** 会话 ID（前端用 crypto.randomUUID 生成） */
  session_id: string
  /** 知识库 ID */
  kb_id: string
  /** 用户问题 */
  question: string
  /** 检索 top_k，默认 5（1-50） */
  top_k?: number
  /** 采样温度，默认 0.0（0.0-2.0） */
  temperature?: number
  /** nucleus sampling，默认 1.0（0.0-1.0） */
  top_p?: number
  /** 最大输出 token 数，默认 null */
  max_tokens?: number | null
}

/** 引用来源单条（字段尽量兼容后端实际返回） */
export interface RetrievalContextItem {
  /** 分块编号 */
  chunk_id?: string
  /** 文档编号 */
  document_id?: string
  /** 相似度分数 */
  score?: number
  /** 内容摘要 */
  content?: string
  /** 检索通道（如有） */
  retrieval_channel?: string
  /** 兼容后端扩展字段 */
  [k: string]: unknown
}

/** 前端本地消息（用于流式展示，不与后端 ChatMessageOut 混用） */
export interface ChatMessage {
  /** 前端生成的主键 */
  id: string
  /** 角色：user / assistant */
  role: 'user' | 'assistant'
  /** 内容（assistant 在 delta 期间逐步追加） */
  content: string
  /** 助手消息状态：sending（开始生成）→ receiving（生成中）→ done / error */
  status: 'sending' | 'receiving' | 'done' | 'error'
  /** 追踪编号（start / done / error 事件携带） */
  trace_id: string
  /** 错误信息（中文） */
  error_message: string
  /** 引用来源（done 事件携带时填充，否则 null） */
  retrieval_context: RetrievalContextItem[] | null
  /** 创建时间（ISO） */
  created_at: string
}

