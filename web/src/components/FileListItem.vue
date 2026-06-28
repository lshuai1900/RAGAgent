<script setup lang="ts">
/**
 * 文件列表行（P1.6 知识库工作台 / Yuxi 风格）
 * - 左侧：文件类型徽标
 * - 中间：文件名（长名省略）+ 浅色元信息（大小 · 时间）
 * - 右侧：状态徽标（已入库 / 处理中 / 等待处理 / 处理失败）+ 操作菜单（重命名 / 删除 / 重新处理）
 * - 失败行展示错误提示入口（Tooltip）
 * - 行底细分隔线，hover 淡灰背景
 *
 * 操作菜单可用性：
 * - 已入库（completed）/ 处理失败（failed）：三项全可用
 * - 待处理（pending）/ 处理中（processing）：
 *   - 重命名 / 删除：可用（用户可在处理过程中取消或改名）
 *   - 重新处理：禁用，提示"文档处理中，暂无法重新处理"
 */
import { computed } from 'vue'
import { Tooltip, Dropdown, Menu, MenuItem, MenuDivider } from 'ant-design-vue'
import {
  CheckCircle2,
  XCircle,
  Loader,
  Clock,
  AlertCircle,
  MoreHorizontal,
  Pencil,
  Trash2,
  RefreshCw,
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
  /** 操作进行中（重命名 / 删除 / 重新处理），用于禁用菜单避免重复提交 */
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

/** 菜单项是否禁用 */
const menuDisabled = computed(() => Boolean(props.actionLoading))

function handleRename(): void {
  if (menuDisabled.value) return
  emit('rename', props.document)
}
function handleDelete(): void {
  if (menuDisabled.value) return
  emit('delete', props.document)
}
function handleReprocess(): void {
  if (menuDisabled.value || reprocessDisabledReason.value) return
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

      <!-- 操作菜单：重命名 / 删除 / 重新处理 -->
      <Dropdown placement="bottomRight" :trigger="['click']">
        <button
          type="button"
          class="file-item__more"
          :disabled="menuDisabled"
          :title="menuDisabled ? '操作进行中…' : '更多操作'"
          @click.stop
        >
          <MoreHorizontal :size="16" />
        </button>
        <template #overlay>
          <Menu class="file-item__menu">
            <MenuItem key="rename" :disabled="menuDisabled" @click="handleRename">
              <template #icon><Pencil :size="14" /></template>
              重命名
            </MenuItem>
            <MenuItem
              key="reprocess"
              :disabled="menuDisabled || Boolean(reprocessDisabledReason)"
              :title="reprocessDisabledReason"
              @click="handleReprocess"
            >
              <template #icon><RefreshCw :size="14" /></template>
              重新处理
              <span v-if="reprocessDisabledReason" class="file-item__menu-hint">
                · {{ reprocessDisabledReason }}
              </span>
            </MenuItem>
            <MenuDivider />
            <MenuItem key="delete" :disabled="menuDisabled" danger @click="handleDelete">
              <template #icon><Trash2 :size="14" /></template>
              删除
            </MenuItem>
          </Menu>
        </template>
      </Dropdown>
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

/* 失败行不做重背景，保持列表清爽，仅状态徽标提示 */

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

/* 更多操作按钮（24×24，浅边框，hover 主色） */
.file-item__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--kb-radius-sm);
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border-strong);
  color: var(--kb-text-secondary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.file-item__more:hover:not(:disabled) {
  color: var(--kb-primary-hover);
  border-color: var(--kb-primary-soft-hover);
  background-color: var(--kb-primary-bg);
}

.file-item__more:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.file-item__menu-hint {
  margin-left: 4px;
  font-size: 12px;
  color: var(--kb-text-tertiary);
}

@keyframes file-item-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
