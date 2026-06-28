<script setup lang="ts">
/**
 * 文件列表行（P1.6 知识库工作台 / Yuxi 风格）
 * - 左侧：文件类型徽标
 * - 中间：文件名（长名省略）+ 浅色元信息（大小 · 时间）
 * - 右侧：状态徽标（已入库 / 处理中 / 等待处理 / 处理失败）
 * - 失败行展示错误提示入口（Tooltip）
 * - 行底细分隔线，hover 淡灰背景
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
  type StatusBadgeKind,
} from '@/utils/status'
import FileTypeIcon from '@/components/FileTypeIcon.vue'

interface Props {
  document: DocumentOut
}
const props = defineProps<Props>()

const kind = computed<StatusBadgeKind>(() =>
  documentStatusBadgeKind(props.document.status),
)
const statusText = computed(() => documentStatusBadgeText(props.document.status))
const hasError = computed(
  () => props.document.status === 'failed' && !!props.document.error_message,
)
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
    </div>
  </div>
</template>

<style scoped>
.file-item {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid var(--kb-border-light);
  transition: background-color 0.15s;
}

.file-item:hover {
  background-color: #f9fafb;
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
  font-weight: 500;
  color: var(--kb-text);
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

.file-item__badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  padding: 3px 10px;
  border-radius: 12px;
  line-height: 1.4;
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

@keyframes file-item-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
