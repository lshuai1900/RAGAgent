<script setup lang="ts">
/**
 * 知识库卡片（P1.8 / Yuxi 风格高保真）
 * - 顶部：蓝绿色圆角图标方块 + 知识库名称 + 状态标签
 * - 中部：描述（两行截断）
 * - 信息条：RAG 知识库 / 文档数量 / 向量维度
 * - 底部：创建时间 + 进入详情入口
 * - hover 时边框变蓝绿色 + 轻微上浮
 */
import { computed } from 'vue'
import { Tag } from 'ant-design-vue'
import { Database, FileText, ArrowRight, Layers } from 'lucide-vue-next'
import type { KnowledgeBaseOut } from '@/types/api'
import {
  knowledgeBaseStatusText,
  knowledgeBaseStatusColor,
  formatTime,
} from '@/utils/format'

interface Props {
  knowledgeBase: KnowledgeBaseOut
}
const props = defineProps<Props>()

interface Emits {
  (e: 'enter', kbId: string): void
}
const emit = defineEmits<Emits>()

const description = computed(() => props.knowledgeBase.description || '暂无描述')

function handleEnter(): void {
  emit('enter', props.knowledgeBase.id)
}
</script>

<template>
  <div class="kb-card" @click="handleEnter">
    <!-- 顶部：图标 + 名称 + 状态 -->
    <div class="kb-card__header">
      <div class="kb-card__icon">
        <Database :size="20" />
      </div>
      <div class="kb-card__heading">
        <span class="kb-card__name" :title="knowledgeBase.name">{{ knowledgeBase.name }}</span>
        <span class="kb-card__type">RAG 知识库</span>
      </div>
      <Tag :color="knowledgeBaseStatusColor(knowledgeBase.status)" class="kb-card__status">
        {{ knowledgeBaseStatusText(knowledgeBase.status) }}
      </Tag>
    </div>

    <!-- 描述 -->
    <p class="kb-card__desc" :title="description">{{ description }}</p>

    <!-- 信息条 -->
    <div class="kb-card__stats">
      <div class="kb-card__stat">
        <FileText :size="13" class="kb-card__stat-icon" />
        <span class="kb-card__stat-label">文档</span>
        <span class="kb-card__stat-value">{{ knowledgeBase.document_count }}</span>
      </div>
      <div class="kb-card__stat">
        <Layers :size="13" class="kb-card__stat-icon" />
        <span class="kb-card__stat-label">维度</span>
        <span class="kb-card__stat-value">{{ knowledgeBase.embedding_dim }}</span>
      </div>
    </div>

    <!-- 底部 -->
    <div class="kb-card__footer">
      <span class="kb-card__time">{{ formatTime(knowledgeBase.created_at) }}</span>
      <span class="kb-card__enter">
        进入详情
        <ArrowRight :size="14" />
      </span>
    </div>
  </div>
</template>

<style scoped>
.kb-card {
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  padding: 18px 18px 14px;
  cursor: pointer;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.kb-card:hover {
  border-color: var(--kb-primary);
  box-shadow: 0 4px 14px rgba(15, 143, 163, 0.08);
  transform: translateY(-1px);
}

.kb-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.kb-card__icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--kb-primary);
  background-color: var(--kb-primary-soft);
}

.kb-card__heading {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-card__name {
  font-weight: 600;
  font-size: 15px;
  color: var(--kb-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.kb-card__type {
  font-size: 11px;
  color: var(--kb-text-tertiary);
  line-height: 1;
}

.kb-card__status {
  flex-shrink: 0;
  margin: 0;
}

.kb-card__desc {
  margin: 0;
  color: var(--kb-text-secondary);
  font-size: 13px;
  line-height: 1.6;
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card__stats {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 0;
  border-top: 1px solid var(--kb-border-light);
  border-bottom: 1px solid var(--kb-border-light);
}

.kb-card__stat {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.kb-card__stat-icon {
  color: var(--kb-text-tertiary);
}

.kb-card__stat-label {
  color: var(--kb-text-tertiary);
}

.kb-card__stat-value {
  color: var(--kb-text);
  font-weight: 600;
}

.kb-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
}

.kb-card__time {
  font-size: 12px;
  color: var(--kb-text-tertiary);
}

.kb-card__enter {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--kb-primary);
  font-weight: 500;
}

.kb-card:hover .kb-card__enter {
  color: var(--kb-primary-hover);
}
</style>
