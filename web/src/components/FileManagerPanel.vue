<script setup lang="ts">
/**
 * 文件管理面板（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi 文件管理信息条，不复制源码）：
 * - 信息条：flex wrap，两端对齐，gap:20px
 *   - 左侧操作：上传（主色按钮 + FileUp 14px）、新建文件夹（次级按钮 + FolderPlus 14px）
 *   - 右侧统计卡片行：gap:8px，每卡 min-width:87px; min-height:36px; padding:5px 10px，
 *     圆角 8px，白底，边框 1px solid #eff2f2，主色图标 16px + 数字(14px/#1e1f1f) + 标签(11px/#979999)
 * - 列表区：复用 DocumentTable（搜索 + 行列表）
 * - 不接后端高级能力：新建文件夹仅提示"后续版本实现"
 */
import { computed } from 'vue'
import { Alert, message } from 'ant-design-vue'
import {
  FileUp,
  FolderPlus,
  RefreshCw,
  Clock,
  Loader,
  CheckCircle2,
  XCircle,
} from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import { documentStatusCategory } from '@/utils/status'
import DocumentTable from '@/components/DocumentTable.vue'

interface Props {
  documents: DocumentOut[]
  loading?: boolean
  /** 文档列表加载错误（中文） */
  error?: string
}
const props = defineProps<Props>()

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
</script>

<template>
  <div class="file-manager">
    <!-- 文件管理信息条：操作 + 统计卡片 -->
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
        <button
          type="button"
          class="file-manager__btn file-manager__btn--secondary"
          @click="handleNewFolder"
        >
          <FolderPlus :size="14" />
          <span>新建文件夹</span>
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
          :disabled="loading"
          :title="loading ? '加载中…' : '刷新列表'"
          @click="handleRefresh"
        >
          <RefreshCw :size="14" :class="{ 'file-manager__spin': loading }" />
        </button>
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

/* ========== 文件管理信息条 ========== */
.file-manager__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
}

/* 左侧操作 */
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
  min-height: 30px;
  padding: 0 12px;
  border-radius: var(--kb-radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
  white-space: nowrap;
}

/* 主色按钮 */
.file-manager__btn--primary {
  background-color: var(--kb-primary);
  border: 1px solid var(--kb-primary);
  color: #ffffff;
}

.file-manager__btn--primary:hover {
  background-color: var(--kb-primary-hover);
  border-color: var(--kb-primary-hover);
}

.file-manager__btn--primary:active {
  background-color: var(--kb-primary-active);
  border-color: var(--kb-primary-active);
}

/* 次级按钮 */
.file-manager__btn--secondary {
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border-strong);
  color: var(--kb-text-secondary);
}

.file-manager__btn--secondary:hover {
  color: var(--kb-text-title);
  border-color: var(--kb-border-hover);
  background-color: var(--kb-bg-hover);
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
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border-light);
  border-radius: var(--kb-radius);
  color: var(--kb-text-title);
}

.file-manager__stat-icon {
  color: var(--kb-primary-hover);
  flex-shrink: 0;
}

.file-manager__stat-icon--spin {
  animation: file-manager-spin 0.9s linear infinite;
}

.file-manager__stat-count {
  font-size: 14px;
  color: var(--kb-text-title);
  font-weight: 600;
  line-height: 1;
}

.file-manager__stat-label {
  font-size: 11px;
  color: var(--kb-text-quaternary);
  line-height: 1;
  margin-left: -2px;
}

/* 刷新图标按钮（24×24） */
.file-manager__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--kb-radius-sm);
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border-strong);
  color: var(--kb-text-secondary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.file-manager__icon-btn:hover {
  color: var(--kb-primary-hover);
  border-color: var(--kb-primary-soft-hover);
  background-color: var(--kb-primary-bg);
}

.file-manager__icon-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.file-manager__spin {
  animation: file-manager-spin 0.9s linear infinite;
}

@keyframes file-manager-spin {
  to {
    transform: rotate(360deg);
  }
}

.file-manager__alert {
  margin-bottom: 0;
}
</style>
