<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式参考 Yuxi DataBaseInfoView 沉浸式 Header，改写为 plain CSS。
-->
<script setup lang="ts">
/**
 * 知识库详情页沉浸式 Header（Yuxi 风格）
 *
 * - 返回按钮 + 知识库图标 + 名称 + 描述 + 状态徽标
 * - 元信息行：文档数量 / 向量维度 / 创建时间 / 更新时间
 * - 操作区：复制 ID / 编辑 / 刷新
 *
 * 不显示暂缓项（模型配置 / 权限 / 知识图谱入口等）。
 */
import { computed } from 'vue'
import { ArrowLeft, Database, Copy, Pencil, RefreshCw, FileText, Layers, Clock } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import YuxiStatusBadge, { type YuxiStatusKind } from '@/components/yuxi/YuxiStatusBadge.vue'
import { formatTime } from '@/utils/format'
import type { KnowledgeBaseOut } from '@/types/api'

interface Props {
  /** 知识库详情（已加载完成时传入） */
  knowledgeBase: KnowledgeBaseOut | null
  /** 加载中（控制刷新按钮 loading 与名称兜底） */
  loading?: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'back'): void
  (e: 'refresh'): void
  (e: 'edit'): void
}
const emit = defineEmits<Emits>()

const displayName = computed(() => props.knowledgeBase?.name ?? '知识库加载中')
const displayDesc = computed(() => props.knowledgeBase?.description || '暂无描述')

const statusKind = computed<YuxiStatusKind>(() => {
  switch (props.knowledgeBase?.status) {
    case 'active':
      return 'success'
    case 'archived':
      return 'default'
    case 'building':
    case 'processing':
    case 'indexing':
      return 'processing'
    case 'failed':
    case 'error':
      return 'error'
    default:
      return 'default'
  }
})

const statusLabel = computed<string>(() => {
  switch (statusKind.value) {
    case 'success':
      return '启用'
    case 'processing':
      return '处理中'
    case 'error':
      return '异常'
    case 'default':
      return '已归档'
    default:
      return '未知'
  }
})

function handleBack(): void {
  emit('back')
}

function handleRefresh(): void {
  emit('refresh')
}

function handleEdit(): void {
  emit('edit')
}

async function handleCopyId(): Promise<void> {
  const kbId = props.knowledgeBase?.id
  if (!kbId) return
  try {
    await navigator.clipboard.writeText(kbId)
    message.success('知识库 ID 已复制')
  } catch {
    message.warning('复制失败，请手动复制')
  }
}
</script>

<template>
  <div class="kb-header">
    <!-- 返回行 -->
    <div class="kb-header__top">
      <button type="button" class="kb-header__back" @click="handleBack">
        <ArrowLeft :size="16" />
        <span>返回知识库</span>
      </button>
    </div>

    <!-- 主体：图标 + 名称 + 描述 + 状态 -->
    <div class="kb-header__main">
      <div class="kb-header__icon">
        <Database :size="22" />
      </div>
      <div class="kb-header__info">
        <div class="kb-header__title-row">
          <h1 class="kb-header__name" :title="displayName">{{ displayName }}</h1>
          <YuxiStatusBadge :kind="statusKind" :label="statusLabel" />
        </div>
        <p class="kb-header__desc">{{ displayDesc }}</p>
      </div>
    </div>

    <!-- 元信息 + 操作 -->
    <div class="kb-header__meta-row">
      <div class="kb-header__meta">
        <div class="kb-header__meta-item">
          <FileText :size="14" />
          <span class="kb-header__meta-label">文档</span>
          <span class="kb-header__meta-value">{{ knowledgeBase?.document_count ?? 0 }}</span>
        </div>
        <div class="kb-header__meta-item">
          <Layers :size="14" />
          <span class="kb-header__meta-label">维度</span>
          <span class="kb-header__meta-value">{{ knowledgeBase?.embedding_dim ?? '—' }}</span>
        </div>
        <div class="kb-header__meta-item">
          <Clock :size="14" />
          <span class="kb-header__meta-label">创建</span>
          <span class="kb-header__meta-value">{{
            knowledgeBase?.created_at ? formatTime(knowledgeBase.created_at) : '—'
          }}</span>
        </div>
        <div class="kb-header__meta-item">
          <Clock :size="14" />
          <span class="kb-header__meta-label">更新</span>
          <span class="kb-header__meta-value">{{
            knowledgeBase?.updated_at ? formatTime(knowledgeBase.updated_at) : '—'
          }}</span>
        </div>
      </div>

      <div class="kb-header__actions">
        <button type="button" class="kb-header__action" @click="handleCopyId">
          <Copy :size="14" />
          <span>复制 ID</span>
        </button>
        <button type="button" class="kb-header__action" @click="handleEdit">
          <Pencil :size="14" />
          <span>编辑</span>
        </button>
        <button
          type="button"
          class="kb-header__action"
          :disabled="loading"
          @click="handleRefresh"
        >
          <RefreshCw :size="14" :class="{ 'kb-header__spin': loading }" />
          <span>刷新</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px var(--kb-page-padding, 24px) 12px;
  background: linear-gradient(180deg, var(--yuxi-main-10) 0%, var(--yuxi-gray-0) 100%);
  border-bottom: 1px solid var(--yuxi-gray-100);
  flex-shrink: 0;
}

/* 返回行 */
.kb-header__top {
  display: flex;
  align-items: center;
}

.kb-header__back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: var(--yuxi-radius-sm);
  color: var(--yuxi-gray-600);
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.kb-header__back:hover {
  background-color: var(--yuxi-gray-100);
  color: var(--yuxi-gray-900);
}

/* 主体 */
.kb-header__main {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.kb-header__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--yuxi-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--yuxi-main-color);
  background-color: var(--yuxi-main-30);
  border: 1px solid var(--yuxi-gray-150);
}

.kb-header__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.kb-header__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.kb-header__name {
  margin: 0;
  font-size: 20px;
  font-weight: 650;
  color: var(--yuxi-gray-900);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.kb-header__desc {
  margin: 0;
  font-size: 13px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
  word-break: break-word;
}

/* 元信息 + 操作行 */
.kb-header__meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.kb-header__meta {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.kb-header__meta-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--yuxi-gray-500);
  font-size: 12px;
}

.kb-header__meta-item svg {
  color: var(--yuxi-gray-400);
}

.kb-header__meta-label {
  color: var(--yuxi-gray-500);
}

.kb-header__meta-value {
  color: var(--yuxi-gray-800);
  font-weight: 500;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

/* 操作按钮组 */
.kb-header__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.kb-header__action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
  background-color: var(--yuxi-gray-0);
  color: var(--yuxi-gray-700);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.18s ease, color 0.18s ease, background-color 0.18s ease;
  white-space: nowrap;
}

.kb-header__action:hover {
  border-color: var(--yuxi-main-100);
  color: var(--yuxi-main-color);
  background-color: var(--yuxi-main-20);
}

.kb-header__action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.kb-header__spin {
  animation: kb-header-spin 1s linear infinite;
}

@keyframes kb-header-spin {
  to {
    transform: rotate(360deg);
  }
}

/* 移动端：元信息纵向堆叠 */
@media (max-width: 767px) {
  .kb-header__meta-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .kb-header__meta {
    gap: 12px;
  }
  .kb-header__actions {
    width: 100%;
  }
  .kb-header__action {
    flex: 1;
    justify-content: center;
  }
}
</style>
