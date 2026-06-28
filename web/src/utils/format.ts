/**
 * 格式化工具：状态文案映射、文件大小、时间
 * 纯函数，不调 api、不访问 store
 */
import dayjs from 'dayjs'
import {
  DocumentStatus,
  type DocumentStatusValue,
  KnowledgeBaseStatus,
  type KnowledgeBaseStatusValue,
} from '@/types/enums'

/** 文档状态 → 中文文案 */
export function documentStatusText(status: string): string {
  switch (status as DocumentStatusValue) {
    case DocumentStatus.PENDING:
      return '待处理'
    case DocumentStatus.PARSING:
      return '解析中'
    case DocumentStatus.CHUNKING:
      return '分块中'
    case DocumentStatus.EMBEDDING:
      return '向量化中'
    case DocumentStatus.INDEXING:
      return '入库中'
    case DocumentStatus.COMPLETED:
      return '已完成'
    case DocumentStatus.FAILED:
      return '失败'
    default:
      return '未知状态'
  }
}

/** 文档状态 → Antd Tag 颜色 */
export function documentStatusColor(status: string): string {
  switch (status as DocumentStatusValue) {
    case DocumentStatus.PENDING:
      return 'default'
    case DocumentStatus.PARSING:
    case DocumentStatus.CHUNKING:
    case DocumentStatus.EMBEDDING:
    case DocumentStatus.INDEXING:
      return 'processing'
    case DocumentStatus.COMPLETED:
      return 'success'
    case DocumentStatus.FAILED:
      return 'error'
    default:
      return 'default'
  }
}

/** 知识库状态 → 中文文案 */
export function knowledgeBaseStatusText(status: string): string {
  switch (status as KnowledgeBaseStatusValue) {
    case KnowledgeBaseStatus.ACTIVE:
      return '启用'
    case KnowledgeBaseStatus.ARCHIVED:
      return '已归档'
    default:
      return '未知状态'
  }
}

/** 知识库状态 → Antd Tag 颜色 */
export function knowledgeBaseStatusColor(status: string): string {
  switch (status as KnowledgeBaseStatusValue) {
    case KnowledgeBaseStatus.ACTIVE:
      return 'success'
    case KnowledgeBaseStatus.ARCHIVED:
      return 'default'
    default:
      return 'default'
  }
}

/** 文件大小格式化：B / KB / MB */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** 时间格式化：YYYY-MM-DD HH:mm */
export function formatTime(value: string | null | undefined): string {
  if (!value) return '-'
  const d = dayjs(value)
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm') : '-'
}

/** 健康检查整体状态 → 中文文案 */
export function healthStatusText(status: string): string {
  switch (status) {
    case 'ok':
      return '正常'
    case 'degraded':
      return '部分异常'
    case 'error':
      return '异常'
    default:
      return '未知'
  }
}

/** 健康检查整体状态 → Antd Tag 颜色 */
export function healthStatusColor(status: string): string {
  switch (status) {
    case 'ok':
      return 'success'
    case 'degraded':
      return 'warning'
    case 'error':
      return 'error'
    default:
      return 'default'
  }
}

/** 组件状态 → 中文文案 */
export function componentStatusText(status: string): string {
  switch (status) {
    case 'ok':
      return '正常'
    case 'error':
      return '异常'
    default:
      return '未知'
  }
}

/** 组件状态 → Antd Tag 颜色 */
export function componentStatusColor(status: string): string {
  switch (status) {
    case 'ok':
      return 'success'
    case 'error':
      return 'error'
    default:
      return 'default'
  }
}
