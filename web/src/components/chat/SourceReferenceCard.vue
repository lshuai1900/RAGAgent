<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 7：Yuxi 风格引用来源卡片，展示单条引用的标题/内容/相似度。
-->
<script setup lang="ts">
/**
 * 引用来源卡片（Step 7）
 *
 * - 标题：filename / documentName / 未知来源
 * - 内容摘要：默认 180-240 字，支持展开/收起，保持换行，不使用 Markdown
 * - 相似度：score 为数字时显示 3 位小数
 * - 分块编号：可选，低调展示
 * - 空内容：显示"暂无片段内容"
 */
import { computed, ref } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'
import type { UiChatReference } from '@/utils/chatReferences'

interface Props {
  /** 引用来源 */
  reference: UiChatReference
  /** 序号（从 1 开始，用于左侧标识） */
  index: number
}
const props = defineProps<Props>()

/** 内容折叠阈值 */
const CONTENT_THRESHOLD = 200

const expanded = ref(false)

/** 展示标题 */
const title = computed(() => {
  return props.reference.filename || props.reference.documentName || '未知来源'
})

/** 原始内容文本 */
const rawContent = computed(() => props.reference.content ?? '')

/** 是否为长内容 */
const isLong = computed(() => rawContent.value.length > CONTENT_THRESHOLD)

/** 展示的内容（折叠时截断） */
const displayContent = computed(() => {
  const text = rawContent.value
  if (!text) return '暂无片段内容'
  if (isLong.value && !expanded.value) {
    return text.slice(0, CONTENT_THRESHOLD) + '…'
  }
  return text
})

/** 相似度文案（3 位小数） */
const scoreText = computed(() => {
  const s = props.reference.score
  if (typeof s === 'number' && Number.isFinite(s)) {
    return `相似度 ${s.toFixed(3)}`
  }
  return ''
})

function toggle(): void {
  expanded.value = !expanded.value
}
</script>

<template>
  <div class="src-card">
    <div class="src-card__index">{{ props.index }}</div>
    <div class="src-card__body">
      <div class="src-card__head">
        <span class="src-card__title" :title="title">{{ title }}</span>
        <span v-if="scoreText" class="src-card__score">{{ scoreText }}</span>
      </div>
      <p class="src-card__content">{{ displayContent }}</p>
      <div class="src-card__footer">
        <span v-if="props.reference.chunkId" class="src-card__chunk">
          分块 {{ props.reference.chunkId }}
        </span>
        <button v-if="isLong" type="button" class="src-card__toggle" @click="toggle">
          <component :is="expanded ? ChevronUp : ChevronDown" :size="13" />
          {{ expanded ? '收起' : '展开' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.src-card {
  display: flex;
  gap: 12px;
  padding: 12px 14px;
  background: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
  transition: border-color 0.15s ease, background-color 0.15s ease;
}

.src-card:hover {
  border-color: var(--yuxi-main-300);
  background: var(--yuxi-main-30);
}

.src-card__index {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--yuxi-main-50);
  color: var(--yuxi-main-700);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.src-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.src-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.src-card__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--yuxi-gray-800);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.src-card__score {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--yuxi-main-600);
  font-variant-numeric: tabular-nums;
}

.src-card__content {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--yuxi-gray-700);
  white-space: pre-wrap;
  word-break: break-word;
}

.src-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.src-card__chunk {
  font-size: 11px;
  color: var(--yuxi-gray-400);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}

.src-card__toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 12px;
  color: var(--yuxi-main-600);
  transition: color 0.15s ease;
}

.src-card__toggle:hover {
  color: var(--yuxi-main-700);
}
</style>
