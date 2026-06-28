/**
 * 格式化工具：知识库/健康状态文案、文件大小、时间
 * 纯函数，不调 api、不访问 store
 * 文档状态相关映射见 utils/status.ts
 */
import dayjs from 'dayjs'
import {
  KnowledgeBaseStatus,
  type KnowledgeBaseStatusValue,
} from '@/types/enums'

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
