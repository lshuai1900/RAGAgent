<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式参考 Yuxi InfoCard，改写为 plain CSS。
-->
<script setup lang="ts">
/**
 * 知识库卡片（Yuxi 风格）
 *
 * - 头部：图标 + 名称 + 副标题 + YuxiStatusBadge
 * - 描述：最多 2 行
 * - 标签：RAG 知识库 + 向量维度
 * - footer：创建时间 + 文档数
 * - hover：边框高亮 + 轻微上浮
 */
import { computed } from 'vue'
import { Database, FileText, Layers } from 'lucide-vue-next'
import type { KnowledgeBaseOut } from '@/types/api'
import { formatTime } from '@/utils/format'
import YuxiStatusBadge, { type YuxiStatusKind } from '@/components/yuxi/YuxiStatusBadge.vue'

interface Props {
  knowledgeBase: KnowledgeBaseOut
}
const props = defineProps<Props>()

interface Emits {
  (e: 'enter', kbId: string): void
}
const emit = defineEmits<Emits>()

const description = computed(() => props.knowledgeBase.description || '暂无描述')

/** 状态 → YuxiStatusBadge kind + 文案 */
const statusKind = computed<YuxiStatusKind>(() => {
  switch (props.knowledgeBase.status) {
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

function handleEnter(): void {
  emit('enter', props.knowledgeBase.id)
}
</script>

<template>
  <div class="kb-card" @click="handleEnter">
    <!-- 头部：图标 + 名称/副标题 + 状态徽标 -->
    <div class="kb-card__header">
      <div class="kb-card__icon">
        <Database :size="20" />
      </div>
      <div class="kb-card__heading">
        <span class="kb-card__name" :title="knowledgeBase.name">{{ knowledgeBase.name }}</span>
        <span class="kb-card__subtitle">RAG 知识库 · {{ knowledgeBase.document_count }} 文件</span>
      </div>
      <YuxiStatusBadge :kind="statusKind" :label="statusLabel" :dot="false" />
    </div>

    <!-- 描述（最多 2 行） -->
    <p class="kb-card__desc" :title="description">{{ description }}</p>

    <!-- 标签 pill -->
    <div class="kb-card__tags">
      <span class="kb-card__tag kb-card__tag--primary">
        <Database :size="11" />
        RAG 知识库
      </span>
      <span class="kb-card__tag">
        <Layers :size="11" />
        {{ knowledgeBase.embedding_dim }} 维
      </span>
    </div>

    <!-- footer -->
    <div class="kb-card__footer">
      <span class="kb-card__footer-time">{{ formatTime(knowledgeBase.created_at) }}</span>
      <span class="kb-card__footer-stat">
        <FileText :size="12" />
        {{ knowledgeBase.document_count }} 文档
      </span>
    </div>
  </div>
</template>

<style scoped>
.kb-card {
  background-image: linear-gradient(45deg, var(--yuxi-gray-0) 0%, var(--yuxi-gray-25) 100%);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
  padding: 16px;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background-image 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.kb-card:hover {
  border-color: var(--yuxi-main-100);
  background-image: linear-gradient(45deg, var(--yuxi-gray-0) 0%, var(--yuxi-main-30) 100%);
  box-shadow: 0 4px 12px var(--yuxi-shadow-1);
  transform: translateY(-1px);
}

/* 头部 */
.kb-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.kb-card__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--yuxi-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--yuxi-main-color);
  background-color: var(--yuxi-main-30);
  border: 1px solid var(--yuxi-gray-150);
}

.kb-card__heading {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kb-card__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.kb-card__subtitle {
  font-size: 12px;
  color: var(--yuxi-gray-600);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 描述 */
.kb-card__desc {
  margin: 0;
  color: var(--yuxi-gray-600);
  font-size: 13px;
  line-height: 1.4;
  min-height: 2.8em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 标签 pill */
.kb-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.kb-card__tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--yuxi-radius-pill);
  font-size: 11px;
  font-weight: 500;
  color: var(--yuxi-gray-600);
  background-color: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  white-space: nowrap;
}

.kb-card__tag--primary {
  color: var(--yuxi-main-700);
  background-color: var(--yuxi-main-50);
  border-color: var(--yuxi-main-100);
}

/* footer */
.kb-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin: 6px -16px -16px;
  border-top: 1px solid var(--yuxi-gray-100);
  background-color: var(--yuxi-gray-10);
  border-radius: 0 0 var(--yuxi-radius) var(--yuxi-radius);
}

.kb-card__footer-time {
  font-size: 12px;
  color: var(--yuxi-gray-500);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.kb-card__footer-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--yuxi-gray-600);
}
</style>
