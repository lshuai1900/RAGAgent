<script setup lang="ts">
/**
 * 文档表格
 * - 列：文件名 / 文件类型 / 状态 / 分块数量 / Token 数量 / 错误信息 / 创建时间 / 操作
 * - 操作列本轮仅"刷新状态"
 * - 文件名搜索 + 状态分组过滤（前端本地过滤）
 * - 处理中状态行有视觉提示
 */
import { computed, ref } from 'vue'
import { Table, Tag, Input, Select, Button, Tooltip, Empty } from 'ant-design-vue'
import { RefreshCw, Search, FileWarning, Loader } from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { formatTime } from '@/utils/format'
import {
  documentStatusText,
  documentStatusColor,
  documentStatusCategory,
  isProcessingDocumentStatus,
  isTerminalDocumentStatus,
  fileTypeText,
  type DocumentStatusCategory,
} from '@/utils/status'

interface Props {
  documents: DocumentOut[]
  loading?: boolean
  /** 正在刷新状态的文档 id（用于按钮 loading） */
  refreshingId?: string
}
const props = defineProps<Props>()

interface Emits {
  (e: 'refresh-status', documentId: string): void
}
const emit = defineEmits<Emits>()

const keyword = ref<string>('')
const statusFilter = ref<DocumentStatusCategory | 'all'>('all')

const filtered = computed<DocumentOut[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  return props.documents.filter((doc) => {
    if (kw && !doc.name.toLowerCase().includes(kw)) return false
    if (statusFilter.value !== 'all') {
      if (documentStatusCategory(doc.status) !== statusFilter.value) return false
    }
    return true
  })
})

const columns = computed(() => [
  { title: '文件名', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '文件类型', dataIndex: 'file_type', key: 'file_type', width: 110 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '分块数量', dataIndex: 'chunk_count', key: 'chunk_count', width: 100, align: 'right' as const },
  { title: 'Token 数量', dataIndex: 'total_tokens', key: 'total_tokens', width: 110, align: 'right' as const },
  { title: '错误信息', dataIndex: 'error_message', key: 'error_message', ellipsis: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 150 },
  { title: '操作', key: 'action', width: 110, fixed: 'right' as const },
])

function rowClassName(record: DocumentOut): string {
  if (isProcessingDocumentStatus(record.status)) return 'doc-row--processing'
  if (record.status === 'failed') return 'doc-row--failed'
  return ''
}

function handleRefresh(documentId: string): void {
  emit('refresh-status', documentId)
}
</script>

<template>
  <div class="doc-table">
    <!-- 搜索与过滤 -->
    <div class="doc-table__toolbar">
      <Input
        v-model:value="keyword"
        placeholder="搜索文档名称"
        allow-clear
        class="doc-table__search"
      >
        <template #prefix><Search :size="14" /></template>
      </Input>
      <Select
        v-model:value="statusFilter"
        class="doc-table__filter"
        :options="[
          { value: 'all', label: '全部状态' },
          { value: 'pending', label: '等待处理' },
          { value: 'processing', label: '处理中' },
          { value: 'completed', label: '已完成' },
          { value: 'failed', label: '处理失败' },
        ]"
      />
    </div>

    <Table
      :data-source="filtered"
      :columns="columns"
      :loading="loading"
      :pagination="false"
      size="small"
      row-key="id"
      :scroll="{ x: 980 }"
      :row-class-name="rowClassName"
    >
      <template #emptyText>
        <Empty description="暂无文档，点击右上角上传" />
      </template>

      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <span class="doc-table__name" :title="record.name">{{ record.name }}</span>
        </template>

        <template v-else-if="column.key === 'file_type'">
          <Tag>{{ fileTypeText(record.file_type) }}</Tag>
        </template>

        <template v-else-if="column.key === 'status'">
          <Tag :color="documentStatusColor(record.status)" class="doc-table__status">
            <Loader v-if="isProcessingDocumentStatus(record.status)" :size="12" class="doc-table__spin" />
            {{ documentStatusText(record.status) }}
          </Tag>
        </template>

        <template v-else-if="column.key === 'chunk_count'">
          {{ isTerminalDocumentStatus(record.status) ? record.chunk_count : '-' }}
        </template>

        <template v-else-if="column.key === 'total_tokens'">
          {{ isTerminalDocumentStatus(record.status) ? record.total_tokens : '-' }}
        </template>

        <template v-else-if="column.key === 'error_message'">
          <Tooltip v-if="record.error_message" :title="record.error_message">
            <span class="doc-table__error">
              <FileWarning :size="13" />
              {{ record.error_message }}
            </span>
          </Tooltip>
          <span v-else class="doc-table__dash">-</span>
        </template>

        <template v-else-if="column.key === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>

        <template v-else-if="column.key === 'action'">
          <Button
            type="link"
            size="small"
            :loading="refreshingId === record.id"
            @click="handleRefresh(record.id)"
          >
            <template #icon><RefreshCw :size="14" /></template>
            刷新状态
          </Button>
        </template>
      </template>
    </Table>
  </div>
</template>

<style scoped>
.doc-table__toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.doc-table__search {
  max-width: 280px;
}

.doc-table__filter {
  width: 150px;
}

.doc-table__name {
  font-weight: 500;
  color: var(--app-text);
}

.doc-table__status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.doc-table__error {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #cf1322;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-table__dash {
  color: var(--app-text-tertiary);
}

/* 处理中行：浅蓝背景 */
:deep(.doc-row--processing td) {
  background-color: #f0f7ff !important;
}

:deep(.doc-row--failed td) {
  background-color: #fff2f0 !important;
}

.doc-table__spin {
  animation: doc-spin 0.8s linear infinite;
}

@keyframes doc-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
