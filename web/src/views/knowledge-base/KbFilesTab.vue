<script setup lang="ts">
/**
 * 知识库详情页 - 文件管理 Tab（子路由视图）
 *
 * 复用已有 FileManagerPanel + 文档操作逻辑（上传/重命名/删除/重新处理/轮询）。
 * 本文件仅做路由适配，kbId 从 route.params 注入。
 */
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Modal, message } from 'ant-design-vue'
import { useDocumentStore } from '@/stores/document'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { ApiError, NetworkError } from '@/api/client'
import type { DocumentOut } from '@/types/api'
import FileManagerPanel from '@/components/FileManagerPanel.vue'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'
import DocumentRenameModal from '@/components/DocumentRenameModal.vue'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId ?? ''))

const docStore = useDocumentStore()
const kbStore = useKnowledgeBaseStore()
const {
  list: docList,
  listState: docListState,
  listError: docListError,
  renaming,
  deleting,
  reprocessing,
} = storeToRefs(docStore)

const uploadModalOpen = ref<boolean>(false)
const renameModalOpen = ref<boolean>(false)
const renameTarget = ref<DocumentOut | null>(null)

const isDocLoading = computed(() => docListState.value === 'loading')
const isDocError = computed(() => docListState.value === 'error' && !isDocLoading.value)
const docActionLoading = computed(
  () => renaming.value || deleting.value || reprocessing.value
)

function refresh(): void {
  if (kbId.value) void docStore.fetchList(kbId.value)
}

function openUpload(): void {
  uploadModalOpen.value = true
}

function handleRename(doc: DocumentOut): void {
  renameTarget.value = doc
  renameModalOpen.value = true
}

function handleRenamed(): void {
  if (kbId.value) void kbStore.fetchDetail(kbId.value)
}

function mapDocErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof NetworkError) return err.message
  if (err instanceof ApiError) {
    if (err.code === 10304) return '文件不存在或已被删除'
    if (err.code === 10404) return '知识库不存在或已被删除'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return fallback
}

function handleDelete(doc: DocumentOut): void {
  Modal.confirm({
    title: '删除文件',
    content:
      '删除文件会同时删除该文件对应的向量索引，删除后无法在检索中命中该文件内容。是否继续？',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await docStore.deleteDocument(kbId.value, doc.id)
        message.success('文件已删除')
        void kbStore.fetchDetail(kbId.value)
      } catch (err) {
        message.error(mapDocErrorMessage(err, '删除失败，请稍后重试'))
      }
    },
  })
}

async function handleReprocess(doc: DocumentOut): Promise<void> {
  try {
    await docStore.reprocessDocument(kbId.value, doc.id)
    message.success('已提交重新处理')
  } catch (err) {
    message.error(mapDocErrorMessage(err, '提交重新处理失败，请稍后重试'))
  }
}

onMounted(() => {
  if (kbId.value) void docStore.fetchList(kbId.value)
})

onBeforeUnmount(() => {
  docStore.reset()
})
</script>

<template>
  <FileManagerPanel
    :documents="docList"
    :loading="isDocLoading"
    :error="isDocError ? (docListError || '加载文档列表失败') : ''"
    :action-loading="docActionLoading"
    @upload="openUpload"
    @refresh="refresh"
    @rename="handleRename"
    @delete="handleDelete"
    @reprocess="handleReprocess"
  />

  <DocumentUploadModal v-model:open="uploadModalOpen" :kb-id="kbId" />
  <DocumentRenameModal
    v-model:open="renameModalOpen"
    :kb-id="kbId"
    :document="renameTarget"
    @renamed="handleRenamed"
  />
</template>
