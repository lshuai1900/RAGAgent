<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 5：状态徽标改用 YuxiStatusBadge；元信息补 chunk_count / 更新时间。
-->
<script setup lang="ts">
/**
 * 文件列表行（Yuxi 风格）
 * - 左侧：文件类型徽标
 * - 中间：文件名（长名省略）+ 浅色元信息（大小 · 分块数 · 创建时间 · 更新时间）
 * - 右侧：YuxiStatusBadge + 操作菜单（重命名 / 重新处理 / 删除）
 * - 失败行展示错误提示入口（Tooltip）
 * - 行底细分隔线，hover 淡灰背景
 *
 * 操作菜单可用性：
 * - 已入库（completed）/ 处理失败（failed）：三项全可用
 * - 待处理（pending）/ 处理中（parsing/chunking/embedding/indexing）：
 *   - 重命名 / 删除：可用（用户可在处理过程中取消或改名）
 *   - 重新处理：禁用，提示"文档正在处理中"
 */
import { computed } from 'vue'
import { Tooltip, Dropdown, Menu, MenuItem, MenuDivider } from 'ant-design-vue'
import {
  AlertCircle,
  MoreHorizontal,
  Pencil,
  Trash2,
  RefreshCw,
} from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { formatFileSize, formatTime } from '@/utils/format'
import {
  documentYuxiStatus,
  isProcessingDocumentStatus,
} from '@/utils/status'
import YuxiStatusBadge from '@/components/yuxi/YuxiStatusBadge.vue'
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

const yuxiStatus = computed(() => documentYuxiStatus(props.document.status))

const hasError = computed(
  () => props.document.status === 'failed' && !!props.document.error_message,
)
const statusTooltip = computed(() =>
  hasError.value ? props.document.error_message : yuxiStatus.value.label,
)

/** 是否处于处理中（parsing/chunking/embedding/indexing），重新处理需禁用 */
const isProcessing = computed(() => isProcessingDocumentStatus(props.document.status))
/** 待处理状态：重新处理需禁用 */
const isPending = computed(() => props.document.status === 'pending')
/** 重新处理禁用原因 */
const reprocessDisabledReason = computed(() => {
  if (isProcessing.value) return '文档正在处理中，暂无法重新处理'
  if (isPending.value) return '文档等待处理，暂无法重新处理'
  return ''
})

/** 菜单项是否禁用 */
const menuDisabled = computed(() => Boolean(props.actionLoading))

/** 元信息片段：大小 · 分块数 · 创建时间 · 更新时间（仅当字段存在时展示） */
interface MetaSeg {
  text: string
  title: string
}
const metaSegs = computed<MetaSeg[]>(() => {
  const segs: MetaSeg[] = []
  // 文件大小（始终展示，未知时显示"未知大小"）
  const size = props.document.file_size
  segs.push({
    text: typeof size === 'number' && size >= 0 ? formatFileSize(size) : '未知大小',
    title: '文件大小',
  })
  // 分块数（>0 才展示，0 或缺失显示 "-"）
  const chunkCount = props.document.chunk_count
  segs.push({
    text: typeof chunkCount === 'number' && chunkCount > 0 ? `${chunkCount} 块` : '-',
    title: '分块数',
  })
  // 创建时间
  const createdAt = props.document.created_at
  segs.push({
    text: createdAt ? formatTime(createdAt) : '-',
    title: '创建时间',
  })
  // 更新时间（与创建时间不同才展示）
  const updatedAt = props.document.updated_at
  if (updatedAt && updatedAt !== createdAt) {
    segs.push({
      text: formatTime(updatedAt),
      title: '更新时间',
    })
  }
  return segs
})

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
  <div class="file-item" :class="`file-item--${yuxiStatus.kind}`">
    <FileTypeIcon :file-type="document.file_type" :size="36" />

    <div class="file-item__main">
      <span class="file-item__name" :title="document.name">{{ document.name }}</span>
      <span class="file-item__meta">
        <template v-for="(seg, idx) in metaSegs" :key="seg.title">
          <span v-if="idx > 0" class="file-item__meta-sep">·</span>
          <span :title="seg.title">{{ seg.text }}</span>
        </template>
      </span>
      <!-- 失败行错误信息红色简短提示 -->
      <div v-if="hasError" class="file-item__error">
        <AlertCircle :size="12" />
        <span class="file-item__error-text">{{ document.error_message }}</span>
      </div>
    </div>

    <div class="file-item__status">
      <Tooltip v-if="hasError" :title="document.error_message" placement="topRight">
        <span class="file-item__error-entry">
          <AlertCircle :size="13" />
        </span>
      </Tooltip>
      <Tooltip :title="statusTooltip" placement="topRight">
        <YuxiStatusBadge :kind="yuxiStatus.kind" :label="yuxiStatus.label" />
      </Tooltip>

      <!-- 操作菜单：重命名 / 重新处理 / 删除 -->
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
  align-items: flex-start;
  gap: 14px;
  min-height: 64px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--yuxi-gray-100);
  transition: background-color 0.15s;
}

.file-item:hover {
  background-color: var(--yuxi-gray-50);
}

.file-item__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding-top: 2px;
}

.file-item__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item__meta {
  font-size: 12px;
  color: var(--yuxi-gray-500);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.file-item__meta-sep {
  color: var(--yuxi-gray-300);
  margin: 0 2px;
}

/* 失败行错误信息 */
.file-item__error {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--yuxi-error-700);
  max-width: 100%;
}

.file-item__error-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-item__status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 4px;
}

.file-item__error-entry {
  display: inline-flex;
  align-items: center;
  color: var(--yuxi-error-700);
  cursor: help;
}

/* 更多操作按钮（28×28，浅边框，hover 主色） */
.file-item__more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--yuxi-radius-sm);
  background-color: var(--yuxi-gray-0);
  border: 1px solid var(--yuxi-gray-150);
  color: var(--yuxi-gray-600);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.file-item__more:hover:not(:disabled) {
  color: var(--yuxi-main-color);
  border-color: var(--yuxi-main-100);
  background-color: var(--yuxi-main-20);
}

.file-item__more:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.file-item__menu-hint {
  margin-left: 4px;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

/* 移动端：操作按钮压缩 */
@media (max-width: 767px) {
  .file-item {
    padding: 10px 12px;
    gap: 10px;
  }
  .file-item__name {
    font-size: 13px;
  }
}
</style>
