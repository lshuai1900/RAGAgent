<script setup lang="ts">
/**
 * 文件管理面板（P1.6 知识库工作台 / Yuxi 风格）
 *
 * - 操作区：上传（主色按钮）/ 新建文件夹（次要按钮，本轮规划提示）/ 刷新（图标按钮）
 * - 列表区：复用 DocumentTable（搜索 + 行列表）
 * - 不接后端高级能力：新建文件夹仅提示"后续版本实现"
 */
import { Button, Tooltip, Alert, message } from 'ant-design-vue'
import { Upload, FolderPlus, RefreshCw } from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import DocumentTable from '@/components/DocumentTable.vue'

interface Props {
  documents: DocumentOut[]
  loading?: boolean
  /** 文档列表加载错误（中文） */
  error?: string
}
defineProps<Props>()

interface Emits {
  (e: 'upload'): void
  (e: 'refresh'): void
}
const emit = defineEmits<Emits>()

function handleUpload(): void {
  emit('upload')
}

function handleRefresh(): void {
  emit('refresh')
}

/** 新建文件夹：本轮仅规划提示，不接后端 */
function handleNewFolder(): void {
  message.info('新建文件夹能力将在后续版本实现')
}
</script>

<template>
  <div class="file-manager">
    <!-- 操作区 -->
    <div class="file-manager__actions">
      <div class="file-manager__actions-left">
        <Button type="primary" @click="handleUpload">
          <template #icon><Upload :size="14" /></template>
          上传
        </Button>
        <Tooltip title="后续版本支持">
          <Button @click="handleNewFolder">
            <template #icon><FolderPlus :size="14" /></template>
            新建文件夹
          </Button>
        </Tooltip>
      </div>
      <div class="file-manager__actions-right">
        <Tooltip title="刷新列表">
          <Button
            type="text"
            class="file-manager__icon-btn"
            :loading="loading"
            @click="handleRefresh"
          >
            <template #icon><RefreshCw :size="15" /></template>
          </Button>
        </Tooltip>
      </div>
    </div>

    <!-- 错误提示 -->
    <Alert
      v-if="error"
      type="error"
      show-icon
      :message="error"
      class="file-manager__alert"
    />

    <!-- 文件列表 -->
    <DocumentTable :documents="documents" :loading="loading" />
  </div>
</template>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.file-manager__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.file-manager__actions-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-manager__actions-right {
  display: flex;
  align-items: center;
}

.file-manager__icon-btn {
  color: var(--kb-text-secondary);
}

.file-manager__icon-btn:hover {
  color: var(--kb-primary);
}

.file-manager__alert {
  margin-bottom: 0;
}
</style>
