<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 5：toolbar + 状态过滤 + loading/empty/error/list 整合；Yuxi 风格 YuxiCard / YuxiEmptyState。
-->
<script setup lang="ts">
/**
 * 文件管理面板（Yuxi 风格）
 *
 * 结构：
 * - toolbar：左侧文件统计/状态摘要 + 右侧刷新 + 上传
 * - 状态过滤 tabs：全部 / 处理中 / 已完成 / 失败（本地过滤，不调后端）
 * - content：loading / error / empty / file list
 *
 * 透传 rename / delete / reprocess 事件给父组件（由详情页接线弹窗 / 确认 / store 调用）。
 * 不实现上传面板内部 UI（保留入口，Step 6 处理）。
 */
import { computed, ref } from 'vue'
import { Spin } from 'ant-design-vue'
import {
  FileUp,
  RefreshCw,
  Clock,
  Loader,
  CheckCircle2,
  XCircle,
  FileText,
  AlertCircle,
} from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { documentStatusCategory } from '@/utils/status'
import DocumentTable, { type DocumentFilterKey } from '@/components/DocumentTable.vue'
import YuxiCard from '@/components/yuxi/YuxiCard.vue'
import YuxiEmptyState from '@/components/yuxi/YuxiEmptyState.vue'

interface Props {
  documents: DocumentOut[]
  loading?: boolean
  /** 后台刷新中（不影响列表骨架，但刷新按钮转圈） */
  refreshing?: boolean
  /** 文档列表加载错误（中文） */
  error?: string
  /** 操作进行中（重命名 / 删除 / 重新处理），透传给 FileListItem 禁用菜单 */
  actionLoading?: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'upload'): void
  (e: 'refresh'): void
  (e: 'rename', document: DocumentOut): void
  (e: 'delete', document: DocumentOut): void
  (e: 'reprocess', document: DocumentOut): void
}
const emit = defineEmits<Emits>()

function handleUpload(): void {
  emit('upload')
}

function handleRefresh(): void {
  emit('refresh')
}

function handleRename(doc: DocumentOut): void {
  emit('rename', doc)
}
function handleDelete(doc: DocumentOut): void {
  emit('delete', doc)
}
function handleReprocess(doc: DocumentOut): void {
  emit('reprocess', doc)
}

/** 各状态文档数量统计 */
const stats = computed(() => {
  let pending = 0
  let processing = 0
  let completed = 0
  let failed = 0
  for (const doc of props.documents) {
    switch (documentStatusCategory(doc.status)) {
      case 'pending':
        pending += 1
        break
      case 'processing':
        processing += 1
        break
      case 'completed':
        completed += 1
        break
      case 'failed':
        failed += 1
        break
    }
  }
  return { pending, processing, completed, failed }
})

interface StatCard {
  key: string
  label: string
  count: number
  icon: typeof Clock
}

const statCards = computed<StatCard[]>(() => [
  { key: 'pending', label: '等待处理', count: stats.value.pending, icon: Clock },
  { key: 'processing', label: '处理中', count: stats.value.processing, icon: Loader },
  { key: 'completed', label: '已入库', count: stats.value.completed, icon: CheckCircle2 },
  { key: 'failed', label: '处理失败', count: stats.value.failed, icon: XCircle },
])

/** 状态过滤 */
const filter = ref<DocumentFilterKey>('all')

const filterTabs: { key: DocumentFilterKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'processing', label: '处理中' },
  { key: 'completed', label: '已完成' },
  { key: 'failed', label: '失败' },
]

function setFilter(key: DocumentFilterKey): void {
  filter.value = key
}

/** 顶部展示 loading 状态（首次加载且无数据时） */
const showLoadingState = computed(
  () => Boolean(props.loading) && props.documents.length === 0,
)
/** 顶部展示错误状态（首次加载失败且无数据时） */
const showErrorState = computed(
  () => Boolean(props.error) && props.documents.length === 0,
)
/** 顶部展示空状态 */
const showEmptyState = computed(
  () => !props.loading && !props.error && props.documents.length === 0,
)
</script>

<template>
  <div class="file-manager">
    <!-- ===== 文件管理信息条：操作 + 统计卡片 ===== -->
    <div class="file-manager__bar">
      <!-- 左侧操作 -->
      <div class="file-manager__actions">
        <button
          type="button"
          class="file-manager__btn file-manager__btn--primary"
          @click="handleUpload"
        >
          <FileUp :size="14" />
          <span>上传</span>
        </button>
      </div>

      <!-- 右侧统计卡片 + 刷新 -->
      <div class="file-manager__right">
        <div class="file-manager__stats">
          <div
            v-for="card in statCards"
            :key="card.key"
            class="file-manager__stat"
            :title="`${card.label}：${card.count}`"
          >
            <component
              :is="card.icon"
              :size="16"
              :class="{
                'file-manager__stat-icon--spin': card.key === 'processing' && card.count > 0,
              }"
              class="file-manager__stat-icon"
            />
            <span class="file-manager__stat-count">{{ card.count }}</span>
            <span class="file-manager__stat-label">{{ card.label }}</span>
          </div>
        </div>
        <button
          type="button"
          class="file-manager__icon-btn"
          :disabled="loading || refreshing"
          :title="loading || refreshing ? '加载中…' : '刷新列表'"
          @click="handleRefresh"
        >
          <RefreshCw
            :size="14"
            :class="{ 'file-manager__spin': loading || refreshing }"
          />
        </button>
      </div>
    </div>

    <!-- ===== 状态过滤 tabs ===== -->
    <nav class="file-manager__filters" role="tablist" aria-label="文档状态过滤">
      <button
        v-for="tab in filterTabs"
        :key="tab.key"
        type="button"
        class="file-manager__filter"
        :class="{ 'file-manager__filter--active': filter === tab.key }"
        role="tab"
        :aria-selected="filter === tab.key"
        @click="setFilter(tab.key)"
      >
        {{ tab.label }}
        <span v-if="filter === tab.key" class="file-manager__filter-count">
          {{
            tab.key === 'all'
              ? documents.length
              : tab.key === 'processing'
                ? stats.processing + stats.pending
                : stats[tab.key]
          }}
        </span>
      </button>
    </nav>

    <!-- ===== content 区 ===== -->
    <!-- loading 状态：骨架屏 -->
    <div v-if="showLoadingState" class="file-manager__state file-manager__state--loading">
      <Spin tip="加载文件列表中..." size="large" />
    </div>

    <!-- error 状态：YuxiCard 包裹错误 -->
    <div v-else-if="showErrorState" class="file-manager__state">
      <YuxiCard flat>
        <div class="file-manager__error">
          <div class="file-manager__error-icon">
            <AlertCircle :size="32" />
          </div>
          <div class="file-manager__error-title">加载文件列表失败</div>
          <div class="file-manager__error-desc">{{ error }}</div>
          <button
            type="button"
            class="file-manager__btn file-manager__btn--primary"
            :disabled="loading"
            @click="handleRefresh"
          >
            <RefreshCw :size="14" :class="{ 'file-manager__spin': loading }" />
            重新加载
          </button>
        </div>
      </YuxiCard>
    </div>

    <!-- empty 状态：YuxiEmptyState -->
    <div v-else-if="showEmptyState" class="file-manager__state">
      <YuxiCard flat>
        <YuxiEmptyState
          :icon="FileText"
          title="暂无文档"
          description="请点击右上角&quot;上传&quot;按钮添加知识库文档"
          full-height
        >
          <template #action>
            <button
              type="button"
              class="file-manager__btn file-manager__btn--primary"
              @click="handleUpload"
            >
              <FileUp :size="14" />
              <span>上传文档</span>
            </button>
          </template>
        </YuxiEmptyState>
      </YuxiCard>
    </div>

    <!-- 文件列表（含搜索 + 过滤） -->
    <DocumentTable
      v-else
      :documents="documents"
      :filter="filter"
      :loading="loading"
      :refreshing="refreshing"
      :action-loading="actionLoading"
      @rename="handleRename"
      @delete="handleDelete"
      @reprocess="handleReprocess"
    />
  </div>
</template>

<style scoped>
.file-manager {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px var(--kb-page-padding, 24px);
}

/* ========== 文件管理信息条 ========== */
.file-manager__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

.file-manager__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 通用按钮（Yuxi extension-panel-action 风格） */
.file-manager__btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 32px;
  padding: 0 14px;
  border-radius: var(--yuxi-radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
  white-space: nowrap;
}

/* 主色按钮 */
.file-manager__btn--primary {
  background-color: var(--yuxi-main-color);
  border: 1px solid var(--yuxi-main-color);
  color: #ffffff;
}

.file-manager__btn--primary:hover {
  background-color: var(--yuxi-main-800);
  border-color: var(--yuxi-main-800);
}

.file-manager__btn--primary:active {
  background-color: var(--yuxi-main-900);
  border-color: var(--yuxi-main-900);
}

.file-manager__btn--primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 右侧区域：统计卡片 + 刷新 */
.file-manager__right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 统计卡片行 */
.file-manager__stats {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* 单张统计卡片 */
.file-manager__stat {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 87px;
  min-height: 36px;
  padding: 5px 10px;
  background-color: var(--yuxi-gray-0);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
  color: var(--yuxi-gray-900);
}

.file-manager__stat-icon {
  color: var(--yuxi-main-color);
  flex-shrink: 0;
}

.file-manager__stat-icon--spin {
  animation: file-manager-spin 0.9s linear infinite;
}

.file-manager__stat-count {
  font-size: 14px;
  color: var(--yuxi-gray-900);
  font-weight: 600;
  line-height: 1;
}

.file-manager__stat-label {
  font-size: 11px;
  color: var(--yuxi-gray-500);
  line-height: 1;
  margin-left: -2px;
}

/* 刷新图标按钮 */
.file-manager__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--yuxi-radius-sm);
  background-color: var(--yuxi-gray-0);
  border: 1px solid var(--yuxi-gray-150);
  color: var(--yuxi-gray-600);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.file-manager__icon-btn:hover:not(:disabled) {
  color: var(--yuxi-main-color);
  border-color: var(--yuxi-main-100);
  background-color: var(--yuxi-main-20);
}

.file-manager__icon-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* ========== 状态过滤 tabs ========== */
.file-manager__filters {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  background-color: var(--yuxi-gray-50);
  border-radius: var(--yuxi-radius);
  align-self: flex-start;
  flex-wrap: wrap;
}

.file-manager__filter {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: none;
  border-radius: var(--yuxi-radius-sm);
  background: transparent;
  color: var(--yuxi-gray-600);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.file-manager__filter:hover {
  color: var(--yuxi-gray-900);
}

.file-manager__filter--active {
  background-color: var(--yuxi-gray-0);
  color: var(--yuxi-main-color);
  font-weight: 600;
  box-shadow: 0 1px 2px var(--yuxi-shadow-1);
}

.file-manager__filter-count {
  font-size: 11px;
  color: inherit;
  opacity: 0.8;
}

/* ========== state 区 ========== */
.file-manager__state {
  flex: 1;
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-manager__state--loading {
  padding: 80px 0;
}

.file-manager__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 24px 32px;
  text-align: center;
}

.file-manager__error-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
  margin-bottom: 6px;
}

.file-manager__error-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.file-manager__error-desc {
  font-size: 13px;
  color: var(--yuxi-gray-600);
  max-width: 480px;
  word-break: break-all;
  margin-bottom: 6px;
}

.file-manager__spin {
  animation: file-manager-spin 0.9s linear infinite;
}

@keyframes file-manager-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 移动端：信息条堆叠 */
@media (max-width: 767px) {
  .file-manager {
    padding: 12px var(--kb-page-padding, 16px);
  }
  .file-manager__bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .file-manager__actions {
    width: 100%;
  }
  .file-manager__btn--primary {
    width: 100%;
    justify-content: center;
  }
  .file-manager__right {
    width: 100%;
    justify-content: space-between;
  }
  .file-manager__stats {
    flex: 1;
    justify-content: flex-start;
  }
}
</style>
