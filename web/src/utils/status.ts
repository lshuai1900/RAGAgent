/**
 * 文档状态映射工具（纯函数，不调 api、不访问 store）
 * 状态文案与颜色严格对齐 docs/FRONTEND_UI_SPEC.md 第 8 节与 .trae/rules/frontend-ui.mdc：
 * - pending：待处理（default）
 * - parsing/chunking/embedding/indexing：处理中（processing）
 * - completed：已完成（success）
 * - failed：失败（error）
 * 另提供 4 分组（等待处理/处理中/已完成/处理失败），用于状态统计卡片与状态过滤。
 *
 * Step 5 新增 documentYuxiStatus：用于 Yuxi 风格文件列表的状态徽标，
 * 文案与 YuxiStatusBadge 对齐（待处理 / 解析中 / 分块中 / 向量化中 / 索引中 / 已完成 / 失败 / 未知）。
 */
import {
  DocumentStatus,
  type DocumentStatusValue,
} from '@/types/enums'
import type { YuxiStatusKind } from '@/components/yuxi/YuxiStatusBadge.vue'

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

/** 文档状态分组（用于统计卡片与过滤） */
export type DocumentStatusCategory = 'pending' | 'processing' | 'completed' | 'failed'

/** 文档状态 → 4 分组 */
export function documentStatusCategory(status: string): DocumentStatusCategory {
  switch (status as DocumentStatusValue) {
    case DocumentStatus.PENDING:
      return 'pending'
    case DocumentStatus.PARSING:
    case DocumentStatus.CHUNKING:
    case DocumentStatus.EMBEDDING:
    case DocumentStatus.INDEXING:
      return 'processing'
    case DocumentStatus.COMPLETED:
      return 'completed'
    case DocumentStatus.FAILED:
      return 'failed'
    default:
      return 'failed'
  }
}

/** 分组 → 中文文案 */
export function documentCategoryText(category: DocumentStatusCategory): string {
  switch (category) {
    case 'pending':
      return '等待处理'
    case 'processing':
      return '处理中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '处理失败'
  }
}

/** 分组 → Antd Tag 颜色 */
export function documentCategoryColor(category: DocumentStatusCategory): string {
  switch (category) {
    case 'pending':
      return 'default'
    case 'processing':
      return 'processing'
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
  }
}

/** 是否为终态（completed / failed） */
export function isTerminalDocumentStatus(status: string): boolean {
  return status === DocumentStatus.COMPLETED || status === DocumentStatus.FAILED
}

/** 是否为处理中状态（parsing/chunking/embedding/indexing） */
export function isProcessingDocumentStatus(status: string): boolean {
  return (
    status === DocumentStatus.PARSING ||
    status === DocumentStatus.CHUNKING ||
    status === DocumentStatus.EMBEDDING ||
    status === DocumentStatus.INDEXING
  )
}

/** 文件类型 → 中文展示（txt→TXT / md→Markdown / pdf→PDF，其他原值大写） */
export function fileTypeText(fileType: string): string {
  const ft = (fileType || '').toLowerCase()
  if (ft === 'txt') return 'TXT'
  if (ft === 'md' || ft === 'markdown') return 'Markdown'
  if (ft === 'pdf') return 'PDF'
  return fileType ? fileType.toUpperCase() : '-'
}

// ===== P1.6 知识库工作台（Yuxi 风格）文件列表状态徽标 =====
// 用于文件管理页行内状态展示，文案与 .trae/rules/frontend-ui.mdc 的表格不同：
// 这里采用更贴近 Yuxi 的工作台文案（已入库 / 处理中 / 等待处理 / 处理失败）。
// 原有 documentStatusText（待处理 / 解析中 / ... / 已完成 / 失败）保留不变，供其它场景使用。

/** 文档状态 → 工作台徽标中文文案 */
export function documentStatusBadgeText(status: string): string {
  const cat = documentStatusCategory(status)
  switch (cat) {
    case 'pending':
      return '等待处理'
    case 'processing':
      return '处理中'
    case 'completed':
      return '已入库'
    case 'failed':
      return '处理失败'
  }
}

/** 文档状态 → 工作台徽标语义类别（用于图标与配色） */
export type StatusBadgeKind = 'success' | 'error' | 'processing' | 'pending'

/** 文档状态 → 工作台徽标语义 */
export function documentStatusBadgeKind(status: string): StatusBadgeKind {
  switch (documentStatusCategory(status)) {
    case 'completed':
      return 'success'
    case 'failed':
      return 'error'
    case 'processing':
      return 'processing'
    case 'pending':
      return 'pending'
  }
}

/**
 * Step 5：Yuxi 风格文件列表状态徽标映射。
 *
 * - pending → processing，文案"待处理"
 * - parsing/chunking/embedding/indexing → processing，文案"解析中/分块中/向量化中/索引中"
 * - completed → success，文案"已完成"
 * - failed → error，文案"失败"
 * - 其他/null → default，文案"未知"
 *
 * 注意：与 documentStatusText 的"入库中/未知状态"文案不同，本函数严格对齐
 * Step 5 验收点 8（待处理/解析中/分块中/向量化中/索引中/已完成/失败/未知）。
 */
export interface DocumentYuxiStatus {
  kind: YuxiStatusKind
  label: string
}

export function documentYuxiStatus(status: string): DocumentYuxiStatus {
  switch (status as DocumentStatusValue) {
    case DocumentStatus.PENDING:
      return { kind: 'processing', label: '待处理' }
    case DocumentStatus.PARSING:
      return { kind: 'processing', label: '解析中' }
    case DocumentStatus.CHUNKING:
      return { kind: 'processing', label: '分块中' }
    case DocumentStatus.EMBEDDING:
      return { kind: 'processing', label: '向量化中' }
    case DocumentStatus.INDEXING:
      return { kind: 'processing', label: '索引中' }
    case DocumentStatus.COMPLETED:
      return { kind: 'success', label: '已完成' }
    case DocumentStatus.FAILED:
      return { kind: 'error', label: '失败' }
    default:
      return { kind: 'default', label: '未知' }
  }
}
