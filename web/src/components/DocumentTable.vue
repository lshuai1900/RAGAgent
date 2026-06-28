<script setup lang="ts">
/**
 * 文档列表（P1.6 知识库工作台 / Yuxi 风格）
 *
 * 改造说明：从原 Antd Table 重表格风格改为 Yuxi 风格的行列表：
 * - 顶部：搜索框（靠左，圆角，浅边框，约 200px）
 * - 列表：FileListItem 行（文件类型徽标 + 文件名 + 状态徽标 + 操作菜单）
 * - 空状态：暂无文档，请点击"上传"添加知识库文档
 * - 仅前端本地按文件名搜索，不接后端
 * - 透传 FileListItem 的 rename / delete / reprocess 事件给父组件
 */
import { computed, ref } from 'vue'
import { Input, Spin, Empty } from 'ant-design-vue'
import { Search } from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import FileListItem from '@/components/FileListItem.vue'

interface Props {
  documents: DocumentOut[]
  loading?: boolean
  /** 操作进行中（重命名 / 删除 / 重新处理），透传给 FileListItem 禁用菜单 */
  actionLoading?: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'rename', document: DocumentOut): void
  (e: 'delete', document: DocumentOut): void
  (e: 'reprocess', document: DocumentOut): void
}
const emit = defineEmits<Emits>()

const keyword = ref<string>('')

const filtered = computed<DocumentOut[]>(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return props.documents
  return props.documents.filter((doc) => doc.name.toLowerCase().includes(kw))
})

/** 无任何文档 */
const isTotalEmpty = computed(
  () => !props.loading && props.documents.length === 0,
)
/** 有文档但搜索无匹配 */
const isNoMatch = computed(
  () => !props.loading && props.documents.length > 0 && filtered.value.length === 0,
)

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
    <!-- 搜索区 -->
    <div class="doc-list__search-row">
      <Input
        v-model:value="keyword"
        placeholder="搜索"
        allow-clear
        class="doc-list__search"
      >
        <template #prefix><Search :size="14" /></template>
      </Input>
    </div>

    <!-- 列表容器 -->
    <div class="doc-list__body">
      <!-- 加载中 -->
      <div v-if="loading" class="doc-list__loading">
        <Spin tip="加载中…" />
      </div>

      <!-- 暂无文档 -->
      <div v-else-if="isTotalEmpty" class="doc-list__empty">
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE">
          <template #description>
            <div class="doc-list__empty-text">
              <div class="doc-list__empty-title">暂无文档</div>
              <div class="doc-list__empty-hint">请点击"上传"添加知识库文档</div>
            </div>
          </template>
        </Empty>
      </div>

      <!-- 搜索无匹配 -->
      <div v-else-if="isNoMatch" class="doc-list__empty">
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="未找到匹配的文档" />
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
}

.doc-list__search {
  width: 280px;
}

.doc-list__body {
  background-color: var(--kb-card-bg);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  min-height: 240px;
  overflow: hidden;
}

.doc-list__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.doc-list__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 70px 0;
}

.doc-list__empty-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.doc-list__empty-title {
  font-size: 14px;
  color: var(--kb-text);
}

.doc-list__empty-hint {
  font-size: 13px;
  color: var(--kb-text-tertiary);
}

.doc-list__items {
  display: flex;
  flex-direction: column;
}

/* 列表首行去除顶部多余间距，由容器边框承载 */
.doc-list__items > :first-child {
  border-top: none;
}
</style>
