<script setup lang="ts">
/**
 * 知识库详情页 - 文件管理 Tab（Yuxi 风格）
 *
 * Step 5 改造：
 * - 接线 FileManagerPanel（toolbar + 状态过滤 + loading/empty/error/list）
 * - 实现 3 秒列表轮询：列表中存在非终态文档时每 3s 刷新一次；全终态停止
 * - 区分 isInitialLoading / isRefreshing：首次加载展示骨架，后台刷新只转圈
 * - 离开 Tab 停止轮询；kbId 变化重启
 * - 文档操作（重命名 / 删除 / 重新处理）弹窗或确认接真实 API
 *
 * store 现有的单文档轮询（2s 间隔）保留不动，列表轮询（3s）作为"主动状态摘要刷新"。
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Modal, message } from 'ant-design-vue'
import { useDocumentStore } from '@/stores/document'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { ApiError, NetworkError } from '@/api/client'
import { isTerminalDocumentStatus } from '@/utils/status'
import type { DocumentOut } from '@/types/api'
import FileManagerPanel from '@/components/FileManagerPanel.vue'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'
import DocumentRenameModal from '@/components/DocumentRenameModal.vue'

/** 列表轮询间隔：3 秒（用户明确要求） */
const POLL_INTERVAL_MS = 3000

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

/** 是否首次加载（无任何数据时） */
const isInitialLoading = computed(
  () => docListState.value === 'loading' && docList.value.length === 0,
)
/** 是否后台刷新中（已有数据时再次 fetchList） */
const isRefreshing = computed(
  () => docListState.value === 'loading' && docList.value.length > 0,
)
/** 是否处于错误状态（首次加载失败且无数据） */
const isDocError = computed(
  () => docListState.value === 'error' && docList.value.length === 0,
)
const docActionLoading = computed(
  () => renaming.value || deleting.value || reprocessing.value,
)

/** 列表中是否存在非终态文档（驱动 3s 轮询） */
const hasNonTerminal = computed(() =>
  docList.value.some((doc) => !isTerminalDocumentStatus(doc.status)),
)

/** 列表轮询定时器 */
let pollTimer: ReturnType<typeof setTimeout> | null = null

/** 清除轮询定时器 */
function clearPollTimer(): void {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

/**
 * 启动 / 调度下一轮列表轮询。
 *
 * 规则：
 * - 列表中存在非终态文档 → 3s 后再次 fetchList
 * - 全部为终态 → 不再调度（停止轮询）
 * - 当前正在请求中 → 不并发，但仍按 3s 调度下一次（store 内部已 abort 旧请求）
 */
function schedulePoll(): void {
  clearPollTimer()
  if (!hasNonTerminal.value) return
  pollTimer = setTimeout(async () => {
    if (kbId.value) {
      await docStore.fetchList(kbId.value)
    }
    // fetchList 完成后递归调度（依据最新 hasNonTerminal）
    schedulePoll()
  }, POLL_INTERVAL_MS)
}

/** 手动刷新：立即触发，避免与轮询并发冲突（store 会 abort 旧请求） */
async function refresh(): Promise<void> {
  if (!kbId.value) return
  await docStore.fetchList(kbId.value)
  schedulePoll()
}

function openUpload(): void {
  uploadModalOpen.value = true
}

/**
 * 上传成功后回调：
 * - store.upload() 内部已 fetchList + startPolling（单文档 2s）
 * - 此处重启列表 3s 轮询（新文档为非终态，schedulePoll 会启动）
 * - 不重复调 fetchList（store 已刷新）
 */
function handleUploaded(): void {
  schedulePoll()
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
    // 文档不存在
    if (err.code === 10304) return '文件不存在或已被删除'
    // 知识库不存在
    if (err.code === 10404) return '知识库不存在或已被删除'
    // 状态冲突（如正在处理中无法删除/重命名）
    if (err.httpStatus === 409) return '文件状态冲突，请刷新后重试'
    // 参数错误
    if (err.httpStatus === 400) return '请求参数不正确，请检查后重试'
    // 服务器错误
    if (err.httpStatus >= 500) return '服务器内部错误，请稍后重试'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return fallback
}

/** 删除文件：二次确认 + DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id} */
function handleDelete(doc: DocumentOut): void {
  Modal.confirm({
    title: '删除文件',
    content: `即将删除文件"${doc.name}"。删除后该文件将不再参与知识库检索，相关索引会按后端逻辑清理。此操作不可撤销，是否继续？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await docStore.deleteDocument(kbId.value, doc.id)
        message.success('文件已删除')
        void kbStore.fetchDetail(kbId.value)
        // 删除后立即刷新列表
        void docStore.fetchList(kbId.value)
      } catch (err) {
        message.error(mapDocErrorMessage(err, '删除失败，请稍后重试'))
      }
    },
  })
}

/**
 * 重新处理文件：二次确认 + POST /api/v1/knowledge-bases/{kb_id}/documents/{document_id}/reprocess
 *
 * 文档处于 pending/parsing/chunking/embedding/indexing 时菜单已禁用，
 * 此处仍做兜底校验，避免后端报状态冲突。
 */
function handleReprocess(doc: DocumentOut): void {
  if (!isTerminalDocumentStatus(doc.status)) {
    message.warning('文档正在处理中，暂无法重新处理')
    return
  }
  Modal.confirm({
    title: '重新处理文件',
    content: `即将重新处理文件"${doc.name}"。重新处理将重新解析、分块、向量化并更新索引。此操作不可撤销，是否继续？`,
    okText: '重新处理',
    cancelText: '取消',
    async onOk() {
      try {
        await docStore.reprocessDocument(kbId.value, doc.id)
        message.success('已提交重新处理')
        // 立即刷新列表 + 启动轮询（reprocessDocument 已更新 list 中的状态）
        schedulePoll()
      } catch (err) {
        message.error(mapDocErrorMessage(err, '提交重新处理失败，请稍后重试'))
      }
    },
  })
}

/** 切换 kbId 时重新加载列表 */
watch(
  kbId,
  async (id, oldId) => {
    if (!id || id === oldId) return
    clearPollTimer()
    await docStore.fetchList(id)
    schedulePoll()
  },
  { immediate: false },
)

onMounted(async () => {
  if (kbId.value) {
    await docStore.fetchList(kbId.value)
    schedulePoll()
  }
})

onBeforeUnmount(() => {
  clearPollTimer()
  docStore.reset()
})
</script>

<template>
  <FileManagerPanel
    :documents="docList"
    :loading="isInitialLoading"
    :refreshing="isRefreshing"
    :error="isDocError ? (docListError || '加载文档列表失败') : ''"
    :action-loading="docActionLoading"
    @upload="openUpload"
    @refresh="refresh"
    @rename="handleRename"
    @delete="handleDelete"
    @reprocess="handleReprocess"
  />

  <DocumentUploadModal
    v-model:open="uploadModalOpen"
    :kb-id="kbId"
    @uploaded="handleUploaded"
  />
  <DocumentRenameModal
    v-model:open="renameModalOpen"
    :kb-id="kbId"
    :document="renameTarget"
    @renamed="handleRenamed"
  />
</template>
