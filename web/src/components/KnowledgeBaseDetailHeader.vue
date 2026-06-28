<script setup lang="ts">
/**
 * 知识库详情页顶部 Header（P1.6 / Yuxi 风格）
 * - 左侧：返回按钮
 * - 知识库图标（数据库/知识库类图标，蓝绿色）
 * - 知识库名称
 * - 副标题：RAG 知识库 · {documentCount} 文件
 * - 右侧：刷新按钮（弱化样式）
 */
import { Button } from 'ant-design-vue'
import { ArrowLeft, Database, RefreshCw } from 'lucide-vue-next'

interface Props {
  /** 知识库名称 */
  name: string
  /** 文件数量（用于副标题） */
  documentCount: number
  /** 知识库信息加载中（控制刷新按钮 loading） */
  loading?: boolean
}
defineProps<Props>()

interface Emits {
  (e: 'back'): void
  (e: 'refresh'): void
}
const emit = defineEmits<Emits>()

function handleBack(): void {
  emit('back')
}

function handleRefresh(): void {
  emit('refresh')
}
</script>

<template>
  <div class="kb-header">
    <Button type="text" class="kb-header__back" @click="handleBack">
      <template #icon><ArrowLeft :size="16" /></template>
      返回
    </Button>

    <div class="kb-header__main">
      <div class="kb-header__icon">
        <Database :size="22" />
      </div>
      <div class="kb-header__text">
        <div class="kb-header__name" :title="name">{{ name }}</div>
        <div class="kb-header__subtitle">
          RAG 知识库 · {{ documentCount }} 文件
        </div>
      </div>
    </div>

    <Button
      type="text"
      class="kb-header__refresh"
      :loading="loading"
      @click="handleRefresh"
    >
      <template #icon><RefreshCw :size="15" /></template>
      刷新
    </Button>
  </div>
</template>

<style scoped>
.kb-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background-color: var(--kb-card-bg);
  border-bottom: 1px solid var(--kb-border);
}

.kb-header__back {
  flex-shrink: 0;
  color: var(--kb-text-secondary);
  padding: 0 4px;
}

.kb-header__back:hover {
  color: var(--kb-primary);
}

.kb-header__main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
}

.kb-header__icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--kb-primary);
  background-color: var(--kb-primary-bg);
}

.kb-header__text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-header__name {
  font-size: 18px;
  font-weight: 600;
  color: var(--kb-text);
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-header__subtitle {
  font-size: 13px;
  color: var(--kb-text-secondary);
}

.kb-header__refresh {
  flex-shrink: 0;
  color: var(--kb-text-secondary);
}

.kb-header__refresh:hover {
  color: var(--kb-primary);
}
</style>
