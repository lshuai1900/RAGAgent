<script setup lang="ts">
/**
 * 知识库卡片：展示知识库基本信息，点击进入详情
 */
import { computed } from 'vue'
import { Tag, Button } from 'ant-design-vue'
import { Database, FileText, ArrowRight } from 'lucide-vue-next'
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
    <div class="kb-card__header">
      <div class="kb-card__title">
        <Database :size="16" class="kb-card__icon" />
        <span class="kb-card__name" :title="knowledgeBase.name">{{ knowledgeBase.name }}</span>
      </div>
      <Tag :color="knowledgeBaseStatusColor(knowledgeBase.status)">
        {{ knowledgeBaseStatusText(knowledgeBase.status) }}
      </Tag>
    </div>

    <p class="kb-card__desc" :title="description">{{ description }}</p>

    <div class="kb-card__tags">
      <Tag color="blue">Milvus</Tag>
      <Tag color="geekblue">向量维度 {{ knowledgeBase.embedding_dim }}</Tag>
      <Tag :color="knowledgeBaseStatusColor(knowledgeBase.status)">
        {{ knowledgeBaseStatusText(knowledgeBase.status) }}
      </Tag>
    </div>

    <div class="kb-card__meta">
      <div class="kb-card__meta-row">
        <FileText :size="13" class="kb-card__meta-icon" />
        <span class="kb-card__meta-label">文档数量</span>
        <span class="kb-card__meta-value">{{ knowledgeBase.document_count }}</span>
      </div>
      <div class="kb-card__meta-row">
        <span class="kb-card__meta-label">集合名称</span>
        <span class="kb-card__meta-value kb-card__meta-mono">{{ knowledgeBase.collection_name }}</span>
      </div>
      <div class="kb-card__meta-row">
        <span class="kb-card__meta-label">创建时间</span>
        <span class="kb-card__meta-value">{{ formatTime(knowledgeBase.created_at) }}</span>
      </div>
    </div>

    <div class="kb-card__footer">
      <Button type="link" size="small" class="kb-card__enter" @click.stop="handleEnter">
        进入详情
        <template #icon><ArrowRight :size="14" /></template>
      </Button>
    </div>
  </div>
</template>

<style scoped>
.kb-card {
  background-color: var(--app-card-bg);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  padding: 16px 18px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.kb-card:hover {
  border-color: #1677ff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.kb-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kb-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.kb-card__icon {
  flex-shrink: 0;
  color: #1677ff;
}

.kb-card__name {
  font-weight: 600;
  font-size: 15px;
  color: var(--app-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-card__desc {
  margin: 0;
  color: var(--app-text-secondary);
  font-size: 13px;
  line-height: 1.6;
  min-height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.kb-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kb-card__meta {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid var(--app-border);
}

.kb-card__meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.kb-card__meta-icon {
  color: var(--app-text-tertiary);
}

.kb-card__meta-label {
  color: var(--app-text-tertiary);
  flex-shrink: 0;
}

.kb-card__meta-value {
  color: var(--app-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-card__meta-mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

.kb-card__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  padding-top: 4px;
}

.kb-card__enter {
  padding: 0 4px;
  height: auto;
  font-size: 13px;
}
</style>
