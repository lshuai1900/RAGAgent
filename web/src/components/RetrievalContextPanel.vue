<script setup lang="ts">
/**
 * 引用来源展示面板
 *
 * - 支持展示多条引用来源，每条以卡片形式渲染
 * - 字段中文展示：分块编号 / 文档编号 / 相似度分数 / 检索通道 / 内容摘要
 * - 内容摘要过长时折叠展示，可展开/收起
 * - score 为数字时保留 3 位小数
 * - 无引用时展示 Empty 状态：暂无引用来源
 * - 不伪造引用来源，后端不下发时显示空状态
 */
import { computed, ref } from 'vue'
import { Card, Empty, Tag } from 'ant-design-vue'
import { FileText, ChevronDown, ChevronUp } from 'lucide-vue-next'
import type { RetrievalContextItem } from '@/types/api'

interface Props {
  /** 引用来源列表，null / undefined / 空数组均视为"暂无引用来源" */
  items?: RetrievalContextItem[] | null
}
const props = defineProps<Props>()

const list = computed<RetrievalContextItem[]>(() => props.items ?? [])
const hasItems = computed(() => list.value.length > 0)

/** 内容摘要折叠阈值（字符数） */
const CONTENT_THRESHOLD = 200

/** 记录每条引用的展开状态（按索引） */
const expandedSet = ref<Set<number>>(new Set())

function isExpanded(idx: number): boolean {
  return expandedSet.value.has(idx)
}

function toggleExpand(idx: number): void {
  const next = new Set(expandedSet.value)
  if (next.has(idx)) {
    next.delete(idx)
  } else {
    next.add(idx)
  }
  expandedSet.value = next
}

/** 判断内容摘要是否超过折叠阈值 */
function isLongContent(content: unknown): boolean {
  if (typeof content !== 'string') return false
  return content.length > CONTENT_THRESHOLD
}

/** 获取截断后的内容摘要 */
function truncatedContent(content: unknown): string {
  const text = fmtText(content)
  if (text.length <= CONTENT_THRESHOLD) return text
  return text.slice(0, CONTENT_THRESHOLD) + '...'
}

/** 相似度分数格式化为 3 位小数 */
function fmtScore(score: unknown): string {
  if (typeof score === 'number' && Number.isFinite(score)) {
    return score.toFixed(3)
  }
  const n = Number(score)
  return Number.isFinite(n) ? n.toFixed(3) : '-'
}

/** 通用文本格式化 */
function fmtText(v: unknown): string {
  if (v === null || v === undefined || v === '') return '-'
  return String(v)
}
</script>

<template>
  <Card class="rcp" :bordered="true" size="small">
    <template #title>
      <div class="rcp__title">
        <FileText :size="14" class="rcp__icon" />
        <span>引用来源</span>
      </div>
    </template>

    <div v-if="!hasItems" class="rcp__empty">
      <Empty
        :image="Empty.PRESENTED_IMAGE_SIMPLE"
        description="暂无引用来源"
      />
    </div>

    <div v-else class="rcp__list">
      <div v-for="(item, idx) in list" :key="idx" class="rcp__item">
        <div class="rcp__item-head">
          <Tag color="blue">引用 {{ idx + 1 }}</Tag>
          <span class="rcp__field">
            <span class="rcp__label">分块编号：</span>
            <span class="rcp__value rcp__value--mono">{{ fmtText(item.chunk_id) }}</span>
          </span>
          <span class="rcp__field">
            <span class="rcp__label">文档编号：</span>
            <span class="rcp__value rcp__value--mono">{{ fmtText(item.document_id) }}</span>
          </span>
          <span class="rcp__field">
            <span class="rcp__label">相似度分数：</span>
            <span class="rcp__value">{{ fmtScore(item.score) }}</span>
          </span>
          <span v-if="item.retrieval_channel" class="rcp__field">
            <span class="rcp__label">检索通道：</span>
            <Tag color="geekblue">{{ fmtText(item.retrieval_channel) }}</Tag>
          </span>
        </div>
        <div class="rcp__content-row">
          <span class="rcp__label">内容摘要：</span>
          <div class="rcp__content-wrap">
            <span v-if="isLongContent(item.content) && !isExpanded(idx)" class="rcp__content">
              {{ truncatedContent(item.content) }}
            </span>
            <span v-else class="rcp__content">{{ fmtText(item.content) }}</span>
            <button
              v-if="isLongContent(item.content)"
              class="rcp__toggle"
              @click="toggleExpand(idx)"
            >
              <component :is="isExpanded(idx) ? ChevronUp : ChevronDown" :size="13" />
              {{ isExpanded(idx) ? '收起' : '展开' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Card>
</template>

<style scoped>
.rcp {
  border-radius: var(--app-radius);
}

.rcp__title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}

.rcp__icon {
  color: #1677ff;
}

.rcp__empty {
  padding: 12px 0;
  display: flex;
  justify-content: center;
}

.rcp__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rcp__item {
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
  padding: 10px 12px;
  background-color: #fafafa;
}

.rcp__item-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.rcp__field {
  display: inline-flex;
  align-items: center;
  font-size: 13px;
}

.rcp__label {
  color: var(--app-text-tertiary);
}

.rcp__value {
  color: var(--app-text-secondary);
}

.rcp__value--mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
}

.rcp__content-row {
  display: flex;
  gap: 4px;
  font-size: 13px;
  line-height: 1.6;
}

.rcp__content-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.rcp__content {
  color: var(--app-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.rcp__toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 12px;
  color: #1677ff;
  align-self: flex-start;
}

.rcp__toggle:hover {
  color: #4096ff;
}

/* 知识库工作台内（检索测试 Tab）轻量视觉统一：图标 / 链接跟随蓝绿色主色 */
:global(.kb-workspace) .rcp__icon {
  color: var(--kb-primary);
}

:global(.kb-workspace) .rcp__item {
  border-color: var(--kb-border);
  border-radius: var(--kb-radius);
  background-color: var(--kb-bg);
}

:global(.kb-workspace) .rcp__toggle {
  color: var(--kb-primary);
}

:global(.kb-workspace) .rcp__toggle:hover {
  color: var(--kb-primary-hover);
}
</style>
