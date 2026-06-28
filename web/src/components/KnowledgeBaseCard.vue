<script setup lang="ts">
/**
 * 知识库卡片（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi InfoCard + ExtensionCardGrid，不复制源码）：
 * - padding:16px，圆角 8px，边框 1px solid #eef0f0
 * - 背景：linear-gradient(45deg, #fff 0%, #f8fafa 100%)
 * - 内部纵向 gap:10px，cursor:pointer
 * - hover：边框 #c4eaf5，背景渐变到 linear-gradient(45deg,#fff,#f7fbfd)，过渡 0.2s
 * - 头部：40×40 图标框（圆角 8px，底 #f7fbfd，边框 #eef0f0，主色字 #046a82）+ 名称（14px/600/#1e1f1f）+ 副标题（12px/#697070 monospace）+ 状态点
 * - 描述：13px/#697070，行高 1.4，最多 2 行，最小高 2.8em
 * - 标签 pill：知识库类型 + 向量维度
 * - footer：padding:10px 16px，顶边框 1px solid #eff2f2，底 #fbfcfc，含创建时间 + 文档数
 */
import { computed } from 'vue'
import { Database, FileText, Layers } from 'lucide-vue-next'
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

/** 状态点颜色（按 Antd Tag color 映射到具体色值） */
const statusDotColor = computed<string>(() => {
  const c = knowledgeBaseStatusColor(props.knowledgeBase.status)
  switch (c) {
    case 'success':
      return 'var(--kb-success)'
    case 'processing':
      return 'var(--kb-processing)'
    case 'warning':
      return 'var(--kb-warning)'
    case 'error':
      return 'var(--kb-error)'
    default:
      return 'var(--kb-text-border-disabled)'
  }
})

function handleEnter(): void {
  emit('enter', props.knowledgeBase.id)
}
</script>

<template>
  <div class="kb-card" @click="handleEnter">
    <!-- 头部：图标 + 名称/副标题 + 状态点 -->
    <div class="kb-card__header">
      <div class="kb-card__icon">
        <Database :size="20" />
      </div>
      <div class="kb-card__heading">
        <span class="kb-card__name" :title="knowledgeBase.name">{{ knowledgeBase.name }}</span>
        <span class="kb-card__subtitle">RAG 知识库 · {{ knowledgeBase.document_count }} 文件</span>
      </div>
      <span
        class="kb-card__status-dot"
        :style="{ backgroundColor: statusDotColor }"
        :title="knowledgeBaseStatusText(knowledgeBase.status)"
      />
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
  background-image: var(--kb-card-bg-gradient);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s ease, background-image 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.kb-card:hover {
  border-color: var(--kb-primary-soft-hover);
  background-image: var(--kb-card-bg-gradient-hover);
  box-shadow: 0 2px 8px var(--kb-shadow-1);
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
  border-radius: var(--kb-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--kb-primary-hover);
  background-color: var(--kb-primary-bg);
  border: 1px solid var(--kb-border);
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
  color: var(--kb-text-title);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.kb-card__subtitle {
  font-size: 12px;
  color: var(--kb-text-tertiary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-card__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  background-color: var(--kb-text-border-disabled);
}

/* 描述 */
.kb-card__desc {
  margin: 0;
  color: var(--kb-text-tertiary);
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
  border-radius: var(--kb-radius-pill);
  font-size: 11px;
  font-weight: 500;
  color: var(--kb-text-tertiary);
  background-color: var(--kb-bg-soft);
  border: 1px solid var(--kb-border);
  white-space: nowrap;
}

.kb-card__tag--primary {
  color: var(--kb-primary-hover);
  background-color: var(--kb-primary-soft);
  border-color: var(--kb-primary-soft-hover);
}

/* footer */
.kb-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin: 6px -16px -16px;
  border-top: 1px solid var(--kb-border-light);
  background-color: var(--kb-bg);
  border-radius: 0 0 var(--kb-radius) var(--kb-radius);
}

.kb-card__footer-time {
  font-size: 12px;
  color: var(--kb-text-quaternary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.kb-card__footer-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--kb-text-tertiary);
}
</style>
