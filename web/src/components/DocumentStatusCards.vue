<script setup lang="ts">
/**
 * 文档状态统计卡片：按 4 分组计数
 * 等待处理 / 处理中 / 已完成 / 处理失败
 */
import { computed } from 'vue'
import { Clock, Loader, CheckCircle2, XCircle } from 'lucide-vue-next'
import type { DocumentOut } from '@/types/api'
import {
  documentStatusCategory,
  documentCategoryText,
  type DocumentStatusCategory,
} from '@/utils/status'

interface Props {
  documents: DocumentOut[]
}
const props = defineProps<Props>()

const CATEGORIES: DocumentStatusCategory[] = ['pending', 'processing', 'completed', 'failed']

const counts = computed<Record<DocumentStatusCategory, number>>(() => {
  const result: Record<DocumentStatusCategory, number> = {
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  }
  for (const doc of props.documents) {
    const cat = documentStatusCategory(doc.status)
    result[cat] += 1
  }
  return result
})

const ICONS: Record<DocumentStatusCategory, unknown> = {
  pending: Clock,
  processing: Loader,
  completed: CheckCircle2,
  failed: XCircle,
}
</script>

<template>
  <div class="doc-stat-cards">
    <div
      v-for="cat in CATEGORIES"
      :key="cat"
      class="doc-stat-card"
      :class="`doc-stat-card--${cat}`"
    >
      <component :is="ICONS[cat]" :size="18" class="doc-stat-card__icon" />
      <div class="doc-stat-card__body">
        <span class="doc-stat-card__count">{{ counts[cat] }}</span>
        <span class="doc-stat-card__label">{{ documentCategoryText(cat) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.doc-stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.doc-stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background-color: var(--app-card-bg);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius);
}

.doc-stat-card__icon {
  flex-shrink: 0;
}

.doc-stat-card--pending .doc-stat-card__icon {
  color: #8c8c8c;
}
.doc-stat-card--processing .doc-stat-card__icon {
  color: #1677ff;
}
.doc-stat-card--completed .doc-stat-card__icon {
  color: #52c41a;
}
.doc-stat-card--failed .doc-stat-card__icon {
  color: #ff4d4f;
}

.doc-stat-card__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.doc-stat-card__count {
  font-size: 22px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--app-text);
}

.doc-stat-card__label {
  font-size: 13px;
  color: var(--app-text-tertiary);
}

@media (max-width: 720px) {
  .doc-stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
