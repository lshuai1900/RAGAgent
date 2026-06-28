<script setup lang="ts">
/**
 * 知识库详情页顶部 top-bar（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi detail-top-bar，不复制源码）：
 * - padding:7px var(--page-padding)，gap:16px，底边框 1px solid #eff2f2，白底
 * - 返回按钮：无边框无底，色 #979999，14px，内边距 4px 8px，margin-left:-8px，圆角 6px
 *   hover：色 #4c4d4d + 底 #f5f7f7
 * - 图标区：40×40，圆角 8px，底 #f7fbfd，边框 #eef0f0，主色图标 18px
 * - 标题：16px/600/#1e1f1f（h2，单行省略）
 * - 副标题：12px/#979999
 * - 操作区：右侧按钮组 gap:8px
 */
import { ArrowLeft, Database, Copy, Pencil, RefreshCw } from 'lucide-vue-next'
import { message } from 'ant-design-vue'

interface Props {
  /** 知识库名称 */
  name: string
  /** 文件数量（用于副标题） */
  documentCount: number
  /** 知识库 ID（用于复制） */
  kbId?: string
  /** 知识库信息加载中（控制刷新按钮 loading） */
  loading?: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'back'): void
  (e: 'refresh'): void
  (e: 'edit'): void
}
const emit = defineEmits<Emits>()

function handleBack(): void {
  emit('back')
}

function handleRefresh(): void {
  emit('refresh')
}

/** 复制知识库 ID（前端剪贴板，不调后端） */
async function handleCopyId(): Promise<void> {
  if (!props.kbId) return
  try {
    await navigator.clipboard.writeText(props.kbId)
    message.success('知识库 ID 已复制')
  } catch {
    message.warning('复制失败，请手动复制')
  }
}

/** 编辑知识库：交由父组件打开编辑弹窗 */
function handleEdit(): void {
  emit('edit')
}
</script>

<template>
  <div class="kb-topbar">
    <!-- 返回按钮 -->
    <button type="button" class="kb-topbar__back" @click="handleBack">
      <ArrowLeft :size="16" />
      <span>返回</span>
    </button>

    <!-- 标题区：图标 + 名称 + 副标题 -->
    <div class="kb-topbar__title-area">
      <div class="kb-topbar__icon">
        <Database :size="18" />
      </div>
      <div class="kb-topbar__text">
        <h2 class="kb-topbar__name" :title="name">{{ name || '知识库加载中' }}</h2>
        <span class="kb-topbar__subtitle">RAG 知识库 · {{ documentCount }} 文件</span>
      </div>
    </div>

    <!-- 操作区 -->
    <div class="kb-topbar__actions">
      <button
        type="button"
        class="kb-topbar__action kb-topbar__action--secondary"
        @click="handleCopyId"
      >
        <Copy :size="14" />
        <span>复制 ID</span>
      </button>
      <button
        type="button"
        class="kb-topbar__action kb-topbar__action--secondary"
        @click="handleEdit"
      >
        <Pencil :size="14" />
        <span>编辑</span>
      </button>
      <button
        type="button"
        class="kb-topbar__action kb-topbar__action--secondary"
        :disabled="loading"
        @click="handleRefresh"
      >
        <RefreshCw :size="14" :class="{ 'kb-topbar__spin': loading }" />
        <span>刷新</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.kb-topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 7px var(--page-padding);
  background-color: var(--kb-surface);
  border-bottom: 1px solid var(--kb-border-light);
  flex-shrink: 0;
}

/* 返回按钮 */
.kb-topbar__back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: -8px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: var(--kb-radius-sm);
  color: var(--kb-text-quaternary);
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  flex-shrink: 0;
}

.kb-topbar__back:hover {
  background-color: var(--kb-bg-hover);
  color: var(--kb-text-secondary);
}

/* 标题区 */
.kb-topbar__title-area {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-topbar__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--kb-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--kb-primary-hover);
  background-color: var(--kb-primary-bg);
  border: 1px solid var(--kb-border);
}

.kb-topbar__text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-topbar__name {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--kb-text-title);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-topbar__subtitle {
  font-size: 12px;
  color: var(--kb-text-quaternary);
}

/* 操作区 */
.kb-topbar__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 通用操作按钮（Yuxi extension-panel-action-secondary） */
.kb-topbar__action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--kb-border-strong);
  border-radius: var(--kb-radius-sm);
  background-color: var(--kb-surface);
  color: var(--kb-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: border-color 0.18s ease, color 0.18s ease, background-color 0.18s ease;
  white-space: nowrap;
}

.kb-topbar__action:hover {
  border-color: var(--kb-border-hover);
  color: var(--kb-text-title);
}

.kb-topbar__action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.kb-topbar__action--secondary:hover {
  color: var(--kb-primary-hover);
  border-color: var(--kb-primary-soft-hover);
}

.kb-topbar__spin {
  animation: kb-topbar-spin 1s linear infinite;
}

@keyframes kb-topbar-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
