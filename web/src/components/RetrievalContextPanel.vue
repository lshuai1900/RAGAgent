<script setup lang="ts">
/**
 * 引用来源展示面板
 *
 * - 后端 SSE done 事件当前不下发 retrieval_context（仅 trace_id + finish_reason）
 * - 本组件按 chunk_id / document_id / score / content / retrieval_channel 字段渲染
 * - 当后端后续在 done 扩展引用来源时，无需改组件即可生效
 * - 无引用时展示"暂无引用来源"
 */
import { computed } from 'vue'
import { Card, Empty, Tag } from 'ant-design-vue'
import { FileText } from 'lucide-vue-next'
import type { RetrievalContextItem } from '@/types/api'

interface Props {
  /** 引用来源列表，null / undefined / 空数组均视为"暂无引用来源" */
  items?: RetrievalContextItem[] | null
}
const props = defineProps<Props>()

const list = computed<RetrievalContextItem[]>(() => props.items ?? [])
const hasItems = computed(() => list.value.length > 0)

/** 相似度分数格式化为 2 位小数 */
function fmtScore(score: unknown): string {
  if (typeof score === 'number' && Number.isFinite(score)) {
    return score.toFixed(2)
  }
  const n = Number(score)
  return Number.isFinite(n) ? n.toFixed(2) : '-'
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
          <span class="rcp__content">{{ fmtText(item.content) }}</span>
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

.rcp__content {
  color: var(--app-text);
  white-space: pre-wrap;
  word-break: break-word;
  flex: 1;
}
</style>
