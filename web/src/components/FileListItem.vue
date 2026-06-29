<script setup lang="ts">
/**
 * 文件列表行（P1.6 知识库工作台 / Yuxi 风格）
 * - 左侧：文件类型徽标
 * - 中间：文件名（长名省略）+ 浅色元信息（大小 · 时间）
 * - 右侧：状态徽标（已入库 / 处理中 / 等待处理 / 处理失败）+ 始终可见的操作按钮（重命名 / 重新处理 / 删除）
 * - 失败行展示错误提示入口（Tooltip）
 * - 行底细分隔线，hover 淡灰背景
 *
 * 操作按钮可用性（按钮始终可见，仅在特定状态下禁用）：
 * - 已入库（completed）/ 处理失败（failed）：三项全可用
 * - 待处理（pending）/ 处理中（processing）：
 *   - 重命名 / 删除：可用（用户可在处理过程中取消或改名）
 *   - 重新处理：禁用，hover 提示"文档处理中，暂无法重新处理"
 */
import { computed } from 'vue'
import { Tooltip } from 'ant-design-vue'
import {
  CheckCircle2,
  XCircle,
  Loader,
  Clock,
  AlertCircle,
} from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { formatFileSize, formatTime } from '@/utils/format'
import {
  documentStatusBadgeText,
  documentStatusBadgeKind,
  isProcessingDocumentStatus,
  type StatusBadgeKind,
} from '@/utils/status'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

interface Props {
  document: DocumentOut
  /** 操作进行中（重命名 / 删除 / 重新处理），用于禁用按钮避免重复提交 */
  actionLoading?: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'rename', document: DocumentOut): void
  (e: 'delete', document: DocumentOut): void
  (e: 'reprocess', document: DocumentOut): void
}
const emit = defineEmits<Emits>()

const kind = computed<StatusBadgeKind>(() =>
  documentStatusBadgeKind(props.document.status),
)
const statusText = computed(() => documentStatusBadgeText(props.document.status))
const hasError = computed(
  () => props.document.status === 'failed' && !!props.document.error_message,
)
const statusTooltip = computed(() =>
  hasError.value ? props.document.error_message : statusText.value,
)

/** 是否处于处理中（parsing/chunking/embedding/indexing），重新处理需禁用 */
const isProcessing = computed(() => isProcessingDocumentStatus(props.document.status))
/** 待处理状态：重新处理需禁用 */
const isPending = computed(() => props.document.status === 'pending')
/** 重新处理禁用原因 */
const reprocessDisabledReason = computed(() => {
  if (isProcessing.value) return '文档处理中，暂无法重新处理'
  if (isPending.value) return '文档等待处理，暂无法重新处理'
  return ''
})

/** 按钮是否禁用（任一操作进行中） */
const buttonsDisabled = computed(() => Boolean(props.actionLoading))
/** 重新处理按钮是否禁用 */
const reprocessDisabled = computed(
  () => buttonsDisabled.value || Boolean(reprocessDisabledReason.value),
)

function handleRename(): void {
  if (buttonsDisabled.value) return
  emit('rename', props.document)
}
function handleDelete(): void {
  if (buttonsDisabled.value) return
  emit('delete', props.document)
}
function handleReprocess(): void {
  if (reprocessDisabled.value) return
  emit('reprocess', props.document)
}
</script>

<template>
  <div class="file-item" :class="`file-item--${kind}`">
    <FileTypeIcon :file-type="document.file_type" :size="36" />

    <div class="file-item__main">
      <span class="file-item__name" :title="document.name">{{ document.name }}</span>
      <span class="file-item__meta">
        {{ formatFileSize(document.file_size) }} · {{ formatTime(document.created_at) }}
      </span>
    </div>

    <div class="file-item__status">
      <Tooltip v-if="hasError" :title="document.error_message" placement="topRight">
        <span class="file-item__error-entry">
          <AlertCircle :size="13" />
        </span>
      </Tooltip>
      <Tooltip :title="statusTooltip" placement="topRight">
        <span class="file-item__badge" :class="`file-item__badge--${kind}`">
          <Loader
            v-if="kind === 'processing'"
            :size="13"
            class="file-item__spin"
          />
          <CheckCircle2 v-else-if="kind === 'success'" :size="13" />
          <XCircle v-else-if="kind === 'error'" :size="13" />
          <Clock v-else :size="13" />
          {{ statusText }}
        </span>
      </Tooltip>

      <!-- 操作按钮：始终可见（重命名 / 重新处理 / 删除），紧邻状态徽标右侧 -->
      <div class="file-item__actions">
        <button
          type="button"
          class="file-item__action"
          :disabled="buttonsDisabled"
          title="重命名"
          @click="handleRename"
        >
          重命名
        </button>
        <button
          type="button"
          class="file-item__action"
          :disabled="reprocessDisabled"
          :title="reprocessDisabledReason || '重新处理'"
          @click="handleReprocess"
        >
          重新处理
        </button>
        <button
          type="button"
          class="file-item__action file-item__action--danger"
          :disabled="buttonsDisabled"
          title="删除"
          @click="handleDelete"
        >
          删除
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-item {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 56px;
  padding: 0 16px;
  border-bottom: 1px solid var(--kb-border-light);
  transition: background-color 0.15s;
}

.file-item:hover {
  background-color: var(--kb-bg-hover);
}

.file-item__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-item__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--kb-text-title);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item__meta {
  font-size: 12px;
  color: var(--kb-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item__status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.file-item__error-entry {
  display: inline-flex;
  align-items: center;
  color: var(--kb-status-error);
  cursor: help;
}

/* 状态 pill：24px 高，pill 圆角 */
.file-item__badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  height: 24px;
  padding: 0 10px;
  border-radius: var(--kb-radius-pill);
  line-height: 1;
  font-weight: 500;
  white-space: nowrap;
}

.file-item__badge--success {
  color: var(--kb-status-success);
  background-color: var(--kb-status-success-bg);
}

.file-item__badge--error {
  color: var(--kb-status-error);
  background-color: var(--kb-status-error-bg);
}

.file-item__badge--processing {
  color: var(--kb-status-processing);
  background-color: var(--kb-status-processing-bg);
}

.file-item__badge--pending {
  color: var(--kb-status-pending);
  background-color: var(--kb-status-pending-bg);
}

.file-item__spin {
  animation: file-item-spin 0.9s linear infinite;
}

/* 操作按钮组：始终可见，紧邻状态徽标右侧 */
.file-item__actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 单个操作按钮：白底浅边 ghost 风格，28px 高，始终可见 */
.file-item__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  min-width: 36px;
  padding: 0 10px;
  border: 1px solid var(--kb-border-strong);
  border-radius: var(--kb-radius-sm);
  background-color: var(--kb-surface);
  color: var(--kb-text-secondary);
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.file-item__action:hover:not(:disabled) {
  color: var(--kb-primary-hover);
  border-color: var(--kb-primary-soft-hover);
  background-color: var(--kb-primary-bg);
}

.file-item__action:active:not(:disabled) {
  background-color: var(--kb-primary-bg-hover);
}

.file-item__action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 删除按钮：危险色文字 */
.file-item__action--danger {
  color: var(--kb-status-error);
}

.file-item__action--danger:hover:not(:disabled) {
  color: var(--kb-status-error);
  border-color: var(--kb-status-error-bg);
  background-color: var(--kb-status-error-bg);
}

@keyframes file-item-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
