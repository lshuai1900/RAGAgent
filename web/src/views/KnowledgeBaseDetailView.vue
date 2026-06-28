<script setup lang="ts">
/**
 * 知识库详情页（Yuxi 风格 1:1 复刻）
 *
 * - 沉浸式布局：route.meta.immersive = true，隐藏全局左侧菜单
 * - 顶部 top-bar：返回 / 知识库图标 / 名称 / 副标题 / 复制 ID / 编辑 / 刷新
 * - 横向 Tab：文件管理 / 检索测试 / 知识图谱 / 知识导图 / RAG 评估 / 评估基准
 *   - 文件管理：真实功能（上传 + 搜索 + 行列表 + 状态轮询）
 *   - 检索测试：真实 SSE 流式问答
 *   - 其余 Tab：规划中，点击提示"该能力将在后续版本实现"
 * - Tab 切换同步 route.query.tab
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Spin, Alert, message } from 'ant-design-vue'
import { Network, Map, BarChart3, ClipboardList } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { useDocumentStore } from '@/stores/document'
import { useChatStore } from '@/stores/chat'
import KnowledgeBaseDetailHeader from '@/components/KnowledgeBaseDetailHeader.vue'
import KnowledgeBaseTabs from '@/components/KnowledgeBaseTabs.vue'
import FileManagerPanel from '@/components/FileManagerPanel.vue'
import SearchTestPanel from '@/components/SearchTestPanel.vue'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'
import KnowledgeBaseEditModal from '@/components/KnowledgeBaseEditModal.vue'

/** 详情页可用 Tab（仅文件管理 / 检索测试为真实功能，其余为规划态） */
type TabKey = 'documents' | 'retrieve'
const VALID_TABS: TabKey[] = ['documents', 'retrieve']

/** 规划中 Tab key（点击仅提示，不切换） */
const PLANNED_TABS = new Set(['graph', 'mindmap', 'eval', 'benchmark'])

/** 规划中 Tab 元信息（用于空态展示） */
const PLANNED_TAB_INFO: Record<string, { label: string; icon: unknown }> = {
  graph: { label: '知识图谱', icon: Network },
  mindmap: { label: '知识导图', icon: Map },
  eval: { label: 'RAG 评估', icon: BarChart3 },
  benchmark: { label: '评估基准', icon: ClipboardList },
}

const route = useRoute()
const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const docStore = useDocumentStore()
const chatStore = useChatStore()
const { detail, detailState, detailError } = storeToRefs(kbStore)
const { list: docList, listState: docListState, listError: docListError } = storeToRefs(docStore)

const kbId = computed(() => String(route.params.kbId ?? ''))

/** 从 route.query.tab 初始化标签页（仅接受真实功能 Tab） */
function readTabFromQuery(): TabKey {
  const t = route.query.tab
  if (typeof t === 'string' && VALID_TABS.includes(t as TabKey)) {
    return t as TabKey
  }
  return 'documents'
}

const activeTab = ref<TabKey>(readTabFromQuery())
const uploadModalOpen = ref<boolean>(false)
const editModalOpen = ref<boolean>(false)

const isKbLoading = computed(() => detailState.value === 'loading')
const isKbError = computed(() => detailState.value === 'error' && !isKbLoading.value)
const isDocLoading = computed(() => docListState.value === 'loading')
const isDocError = computed(() => docListState.value === 'error' && !isDocLoading.value)

/** Header 展示的知识库名称（加载中兜底） */
const headerName = computed(() => detail.value?.name ?? '知识库')

/** Header 副标题文件数：优先后端 document_count，缺失时用当前文档列表数量 */
const documentCount = computed(() => {
  const cnt = detail.value?.document_count
  if (typeof cnt === 'number' && cnt >= 0) return cnt
  return docList.value.length
})

/** Tab 切换处理：规划中 Tab 仅提示，不切换 */
function handleTabSelect(key: string): void {
  if (PLANNED_TABS.has(key)) {
    message.info('该能力将在后续版本实现')
  }
}

/** 真实 Tab 切换：更新 activeTab */
function handleTabUpdate(key: string): void {
  activeTab.value = key as TabKey
}

function goBack(): void {
  router.push('/knowledge-bases')
}

function refreshKb(): void {
  if (kbId.value) {
    void kbStore.fetchDetail(kbId.value)
  }
}

function refreshDocs(): void {
  if (kbId.value) {
    void docStore.fetchList(kbId.value)
  }
}

function openUpload(): void {
  uploadModalOpen.value = true
}

/** 打开编辑知识库弹窗 */
function openEdit(): void {
  editModalOpen.value = true
}

/** 编辑保存成功：store 已同步 detail 与 list，标题由 headerName 计算属性自动更新 */
function handleUpdated(): void {
  // store.updateKb 已更新 detail.value，headerName 会自动反映新名称；
  // 这里再触发一次详情刷新，确保与后端一致。
  if (kbId.value) {
    void kbStore.fetchDetail(kbId.value)
  }
}

/** 删除成功：跳转回知识库列表页 */
function handleDeleted(): void {
  router.push('/knowledge-bases')
}

/** activeTab 变化：同步 URL query，并在进出检索测试时重置聊天 store */
watch(
  activeTab,
  (newTab, oldTab) => {
    if (newTab !== oldTab && (newTab === 'retrieve' || oldTab === 'retrieve')) {
      chatStore.reset()
    }
    if (newTab !== oldTab) {
      router.replace({ query: { ...route.query, tab: newTab } })
    }
  },
)

/** 切换知识库时重置并重新加载 */
watch(
  kbId,
  (id) => {
    if (!id) return
    docStore.reset()
    chatStore.reset()
    void kbStore.fetchDetail(id)
    void docStore.fetchList(id)
  },
  { immediate: false },
)

onMounted(() => {
  if (kbId.value) {
    void kbStore.fetchDetail(kbId.value)
    void docStore.fetchList(kbId.value)
  }
})

onBeforeUnmount(() => {
  docStore.reset()
  chatStore.reset()
  kbStore.resetDetail()
})
</script>

<template>
  <div class="kb-workspace">
    <!-- 顶部 top-bar -->
    <KnowledgeBaseDetailHeader
      :name="headerName"
      :document-count="documentCount"
      :kb-id="kbId"
      :loading="isKbLoading"
      @back="goBack"
      @refresh="refreshKb"
      @edit="openEdit"
    />

    <!-- 横向 Tab 导航 -->
    <KnowledgeBaseTabs
      :model-value="activeTab"
      @update:model-value="handleTabUpdate"
      @select="handleTabSelect"
    />

    <!-- 主体 -->
    <div class="kb-workspace__body">
      <!-- 知识库信息错误 -->
      <Alert
        v-if="isKbError"
        type="error"
        show-icon
        :message="detailError || '加载知识库详情失败'"
        class="kb-workspace__alert"
      />

      <!-- 知识库信息加载中（首次加载，详情尚未就绪） -->
      <div v-else-if="isKbLoading && !detail" class="kb-workspace__loading">
        <Spin tip="加载中..." size="large" />
      </div>

      <template v-else>
        <!-- 文件管理（真实功能） -->
        <FileManagerPanel
          v-if="activeTab === 'documents'"
          :documents="docList"
          :loading="isDocLoading"
          :error="isDocError ? (docListError || '加载文档列表失败') : ''"
          @upload="openUpload"
          @refresh="refreshDocs"
        />

        <!-- 检索测试（真实 SSE 流式问答） -->
        <SearchTestPanel
          v-else-if="activeTab === 'retrieve'"
          :kb-id="kbId"
          :kb-name="detail?.name"
        />

        <!-- 兜底空态（规划中 Tab 不会切换到此，因 PLANNED_TABS 不更新 activeTab） -->
        <div v-else class="kb-workspace__planned">
          <div class="kb-workspace__planned-icon">
            <component
              :is="PLANNED_TAB_INFO[activeTab]?.icon ?? Network"
              :size="24"
              :stroke-width="1.8"
            />
          </div>
          <div class="kb-workspace__planned-title">
            {{ PLANNED_TAB_INFO[activeTab]?.label ?? '功能' }}规划中
          </div>
          <div class="kb-workspace__planned-desc">该能力将在后续版本实现</div>
        </div>
      </template>
    </div>

    <!-- 上传文档弹窗 -->
    <DocumentUploadModal v-model:open="uploadModalOpen" :kb-id="kbId" />

    <!-- 编辑知识库弹窗（重命名 / 描述 / 删除） -->
    <KnowledgeBaseEditModal
      v-model:open="editModalOpen"
      :knowledge-base="detail"
      @updated="handleUpdated"
      @deleted="handleDeleted"
    />
  </div>
</template>

<style scoped>
.kb-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: var(--kb-bg);
  color: var(--kb-text);
}

.kb-workspace__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px var(--page-padding);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.kb-workspace__alert {
  margin-bottom: 0;
}

.kb-workspace__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

/* 规划中 Tab 空态（Yuxi ResourceEmptyState 风格） */
.kb-workspace__planned {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 300px;
  padding: 72px 20px;
  text-align: center;
}

.kb-workspace__planned-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--kb-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-bg);
  border: 1px solid var(--kb-border);
  color: var(--kb-primary-hover);
  margin-bottom: 8px;
}

.kb-workspace__planned-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kb-text-title);
}

.kb-workspace__planned-desc {
  font-size: 14px;
  color: var(--kb-text-tertiary);
  max-width: 360px;
  line-height: 1.6;
}
</style>
