<script setup lang="ts">
/**
 * 知识库详情页（P1.3）
 * - 顶部展示知识库基本信息（名称/描述/状态/向量维度/集合名称/文档数量/创建时间）
 * - 标签页：文件管理（真实功能）/ 检索测试（占位）/ 聊天问答（占位）/ 配置（占位）
 * - 文件管理：状态统计 + 上传 + 文档表格 + 状态轮询
 * - 标签页切换同步 route.query.tab
 */
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  Card,
  Tag,
  Button,
  Spin,
  Empty,
  Alert,
  Tabs,
  TabPane,
  Descriptions,
  DescriptionsItem,
  message,
} from 'ant-design-vue'
import { ArrowLeft, RefreshCw, Upload } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { useDocumentStore } from '@/stores/document'
import { formatApiError } from '@/api/client'
import {
  knowledgeBaseStatusText,
  knowledgeBaseStatusColor,
  formatTime,
} from '@/utils/format'
import DocumentStatusCards from '@/components/DocumentStatusCards.vue'
import DocumentTable from '@/components/DocumentTable.vue'
import DocumentUploadModal from '@/components/DocumentUploadModal.vue'

type TabKey = 'documents' | 'retrieve' | 'chat' | 'config'
const VALID_TABS: TabKey[] = ['documents', 'retrieve', 'chat', 'config']

const route = useRoute()
const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const docStore = useDocumentStore()
const { detail, detailState, detailError } = storeToRefs(kbStore)
const { list: docList, listState: docListState, listError: docListError } = storeToRefs(docStore)

const kbId = computed(() => String(route.params.kbId ?? ''))

/** 从 route.query.tab 初始化标签页 */
function readTabFromQuery(): TabKey {
  const t = route.query.tab
  if (typeof t === 'string' && VALID_TABS.includes(t as TabKey)) {
    return t as TabKey
  }
  return 'documents'
}

const activeTab = ref<TabKey>(readTabFromQuery())
const uploadModalOpen = ref<boolean>(false)
const refreshingDocId = ref<string>('')

const isKbLoading = computed(() => detailState.value === 'loading')
const isKbError = computed(() => detailState.value === 'error' && !isKbLoading.value)
const isDocLoading = computed(() => docListState.value === 'loading')
const isDocError = computed(() => docListState.value === 'error' && !isDocLoading.value)

/** 切换标签页时同步 URL query（replace 避免历史污染） */
function handleTabChange(key: string | number): void {
  const tab = String(key) as TabKey
  activeTab.value = tab
  router.replace({ query: { ...route.query, tab } })
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

/** 操作列：刷新单个文档状态 */
async function handleRefreshStatus(documentId: string): Promise<void> {
  refreshingDocId.value = documentId
  try {
    await docStore.refreshDocument(documentId)
  } catch (err) {
    message.error(formatApiError(err))
  } finally {
    refreshingDocId.value = ''
  }
}

/** 切换知识库时重置并重新加载 */
watch(
  kbId,
  (id) => {
    if (!id) return
    docStore.reset()
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
  // 停止所有轮询并重置文档 store，避免内存泄漏与跨知识库污染
  docStore.reset()
  kbStore.resetDetail()
})
</script>

<template>
  <div class="kb-detail">
    <!-- 顶部：返回 + 刷新 -->
    <div class="kb-detail__topbar">
      <Button type="text" class="kb-detail__back" @click="goBack">
        <template #icon><ArrowLeft :size="16" /></template>
        返回知识库
      </Button>
      <Button :loading="isKbLoading" size="small" @click="refreshKb">
        <template #icon><RefreshCw :size="14" /></template>
        刷新
      </Button>
    </div>

    <!-- 知识库信息加载中 -->
    <div v-if="isKbLoading" class="kb-detail__loading">
      <Spin tip="加载中…" size="large" />
    </div>

    <!-- 知识库信息错误 -->
    <Alert
      v-else-if="isKbError"
      type="error"
      show-icon
      :message="detailError || '加载知识库详情失败'"
    />

    <!-- 基本信息 -->
    <Card v-else-if="detail" class="kb-detail__info" :bordered="true">
      <template #title>
        <div class="kb-detail__info-title">
          <span>{{ detail.name }}</span>
          <Tag :color="knowledgeBaseStatusColor(detail.status)">
            {{ knowledgeBaseStatusText(detail.status) }}
          </Tag>
        </div>
      </template>

      <Descriptions :column="2" size="small" bordered :label-style="{ width: '120px' }">
        <DescriptionsItem label="描述">{{ detail.description || '暂无描述' }}</DescriptionsItem>
        <DescriptionsItem label="状态">
          <Tag :color="knowledgeBaseStatusColor(detail.status)">
            {{ knowledgeBaseStatusText(detail.status) }}
          </Tag>
        </DescriptionsItem>
        <DescriptionsItem label="向量维度">{{ detail.embedding_dim }}</DescriptionsItem>
        <DescriptionsItem label="集合名称">
          <span class="kb-detail__mono">{{ detail.collection_name }}</span>
        </DescriptionsItem>
        <DescriptionsItem label="文档数量">{{ detail.document_count }}</DescriptionsItem>
        <DescriptionsItem label="创建时间">{{ formatTime(detail.created_at) }}</DescriptionsItem>
      </Descriptions>
    </Card>

    <!-- 标签页 -->
    <Card
      v-if="!isKbLoading && !isKbError && detail"
      class="kb-detail__tabs"
      :bordered="true"
      :body-style="{ padding: '0' }"
    >
      <Tabs v-model:active-key="activeTab" class="kb-detail__tabs-inner" @change="handleTabChange">
        <!-- 文件管理（真实功能） -->
        <TabPane key="documents" tab="文件管理">
          <div class="kb-detail__tab-content">
            <!-- 状态统计卡片 -->
            <DocumentStatusCards :documents="docList" />

            <!-- 顶部操作区 -->
            <div class="kb-detail__doc-actions">
              <Button type="primary" @click="openUpload">
                <template #icon><Upload :size="14" /></template>
                上传文档
              </Button>
              <Button :loading="isDocLoading" @click="refreshDocs">
                <template #icon><RefreshCw :size="14" /></template>
                刷新列表
              </Button>
            </div>

            <!-- 文档列表错误提示 -->
            <Alert
              v-if="isDocError"
              type="error"
              show-icon
              :message="docListError || '加载文档列表失败'"
              class="kb-detail__doc-alert"
            />

            <!-- 文档表格 -->
            <DocumentTable
              :documents="docList"
              :loading="isDocLoading"
              :refreshing-id="refreshingDocId"
              @refresh-status="handleRefreshStatus"
            />
          </div>
        </TabPane>

        <!-- 检索测试（占位） -->
        <TabPane key="retrieve" tab="检索测试">
          <div class="kb-detail__placeholder">
            <Empty description="检索测试将在 P1.4 实现" />
          </div>
        </TabPane>

        <!-- 聊天问答（占位） -->
        <TabPane key="chat" tab="聊天问答">
          <div class="kb-detail__placeholder">
            <Empty description="聊天问答将在 P1.4 实现" />
          </div>
        </TabPane>

        <!-- 配置（占位） -->
        <TabPane key="config" tab="配置">
          <div class="kb-detail__placeholder">
            <Empty description="配置能力将在后续实现" />
          </div>
        </TabPane>
      </Tabs>
    </Card>

    <!-- 上传文档弹窗 -->
    <DocumentUploadModal
      v-model:open="uploadModalOpen"
      :kb-id="kbId"
    />
  </div>
</template>

<style scoped>
.kb-detail {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.kb-detail__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-detail__back {
  padding: 0 4px;
}

.kb-detail__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.kb-detail__info,
.kb-detail__tabs {
  border-radius: var(--app-radius);
}

.kb-detail__info-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.kb-detail__mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.kb-detail__tabs-inner {
  padding: 0 24px;
}

.kb-detail__tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0 24px;
}

.kb-detail__doc-actions {
  display: flex;
  gap: 8px;
}

.kb-detail__doc-alert {
  margin-bottom: 0;
}

.kb-detail__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}
</style>
