<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 5：支持按状态过滤（processing/completed/failed），刷新指示器。
-->
<script setup lang="ts">
/**
 * 文档列表（Yuxi 风格）
 *
 * - 顶部：搜索框（靠左，圆角，浅边框）+ 后台刷新指示器
 * - 列表：FileListItem 行
 * - 空状态：根据当前过滤结果展示不同文案
 * - 仅前端本地按文件名搜索 + 状态过滤，不调后端
 * - 透传 FileListItem 的 rename / delete / reprocess 事件给父组件
 */
import { computed, ref } from 'vue'
import { Input, Empty } from 'ant-design-vue'
import { Search, RefreshCw } from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { documentStatusCategory } from '@/utils/status'
import FileListItem from '@/components/FileListItem.vue'

/** 状态过滤 key（由 FileManagerPanel 传入） */
export type DocumentFilterKey = 'all' | 'processing' | 'completed' | 'failed'

interface Props {
  documents: DocumentOut[]
  /** 状态过滤（all/processing/completed/failed），默认 all */
  filter?: DocumentFilterKey
  /** 后台刷新中（仅展示刷新指示器，不显示骨架） */
  refreshing?: boolean
  loading?: boolean
  /** 操作进行中（重命名 / 删除 / 重新处理），透传给 FileListItem 禁用菜单 */
  actionLoading?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  filter: 'all',
  refreshing: false,
  loading: false,
  actionLoading: false,
})

interface Emits {
  (e: 'rename', document: DocumentOut): void
  (e: 'delete', document: DocumentOut): void
  (e: 'reprocess', document: DocumentOut): void
}
const emit = defineEmits<Emits>()

const keyword = ref<string>('')

/** 应用关键字 + 状态过滤 */
const filtered = computed<DocumentOut[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  return props.documents.filter((doc) => {
    // 关键字过滤
    if (kw && !doc.name.toLowerCase().includes(kw)) return false
    // 状态过滤
    if (props.filter === 'all') return true
    const cat = documentStatusCategory(doc.status)
    if (props.filter === 'processing') {
      return cat === 'processing' || cat === 'pending'
    }
    return cat === props.filter
  })
})

/** 无任何文档（仅在 all 过滤且无数据时认为是真"空"） */
const isTotalEmpty = computed(
  () => !props.loading && props.documents.length === 0 && props.filter === 'all',
)
/** 当前过滤无匹配（有文档但搜索/过滤后为空） */
const isNoMatch = computed(
  () => !props.loading && props.documents.length > 0 && filtered.value.length === 0,
)

const noMatchText = computed(() => {
  if (keyword.value.trim()) return '未找到匹配的文档'
  if (props.filter === 'processing') return '当前没有处理中的文档'
  if (props.filter === 'completed') return '当前没有已完成的文档'
  if (props.filter === 'failed') return '当前没有失败的文档'
  return '暂无文档'
})

function handleRename(doc: DocumentOut): void {
  emit('rename', doc)
}
function handleDelete(doc: DocumentOut): void {
  emit('delete', doc)
}
function handleReprocess(doc: DocumentOut): void {
  emit('reprocess', doc)
}
</script>

<template>
  <div class="doc-list">
    <!-- 搜索区 + 刷新指示器 -->
    <div class="doc-list__search-row">
      <Input
        v-model:value="keyword"
        placeholder="搜索文件名"
        allow-clear
        class="doc-list__search"
      >
        <template #prefix><Search :size="14" /></template>
      </Input>
      <span v-if="refreshing" class="doc-list__refreshing">
        <RefreshCw :size="12" class="doc-list__spin" />
        <span>刷新中...</span>
      </span>
    </div>

    <!-- 列表容器 -->
    <div class="doc-list__body">
      <!-- 暂无文档（真·空） -->
      <div v-if="isTotalEmpty" class="doc-list__empty">
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="暂无文档" />
      </div>

      <!-- 搜索/过滤无匹配 -->
      <div v-else-if="isNoMatch" class="doc-list__empty">
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" :description="noMatchText" />
      </div>

      <!-- 文件列表 -->
      <div v-else class="doc-list__items">
        <FileListItem
          v-for="doc in filtered"
          :key="doc.id"
          :document="doc"
          :action-loading="actionLoading"
          @rename="handleRename"
          @delete="handleDelete"
          @reprocess="handleReprocess"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.doc-list__search-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.doc-list__search {
  width: 280px;
}

.doc-list__refreshing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.doc-list__spin {
  animation: doc-list-spin 0.9s linear infinite;
}

.doc-list__body {
  background-color: var(--yuxi-gray-0);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
  min-height: 240px;
  overflow: hidden;
}

.doc-list__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 70px 0;
}

.doc-list__items {
  display: flex;
  flex-direction: column;
}

/* 列表首行去除顶部多余间距，由容器边框承载 */
.doc-list__items > :first-child {
  border-top: none;
}

@keyframes doc-list-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .doc-list__search {
    width: 100%;
  }
}
</style>
