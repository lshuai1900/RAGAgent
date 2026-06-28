/**
 * 枚举常量（与后端 src/ragent/domain/enums.py 值对齐）
 * 仅作前端常量，不依赖后端代码
 */

/** 文档状态机 */
export const DocumentStatus = {
  PENDING: 'pending',
  PARSING: 'parsing',
  CHUNKING: 'chunking',
  EMBEDDING: 'embedding',
  INDEXING: 'indexing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const

export type DocumentStatusValue = (typeof DocumentStatus)[keyof typeof DocumentStatus]

/** 知识库状态 */
export const KnowledgeBaseStatus = {
  ACTIVE: 'active',
  ARCHIVED: 'archived',
} as const

export type KnowledgeBaseStatusValue =
  (typeof KnowledgeBaseStatus)[keyof typeof KnowledgeBaseStatus]
