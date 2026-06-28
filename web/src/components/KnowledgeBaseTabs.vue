<script setup lang="ts">
/**
 * 知识库详情页横向 Tab 导航（P1.6 / Yuxi 风格）
 *
 * 6 个 Tab：文件管理 / 检索测试 / 知识图谱 / 知识导图 / RAG 评估 / 评估基准
 * - 当前选中项：主色文字 + 底部高亮线
 * - 暂未实现的 Tab（知识图谱 / 知识导图 / RAG 评估 / 评估基准）：
 *   展示为"规划中"态，点击不切换，由父组件通过 @select 提示"该能力将在后续版本实现"
 * - 图标 + 中文文本
 */
import { computed } from 'vue'
import {
  FolderTree,
  Search,
  Share2,
  GitBranch,
  BarChart3,
  Target,
} from 'lucide-vue-next'

type TabKey =
  | 'documents'
  | 'retrieve'
  | 'graph'
  | 'mindmap'
  | 'eval'
  | 'benchmark'

interface TabItem {
  key: TabKey
  label: string
  icon: unknown
  planned: boolean
}

const TABS: TabItem[] = [
  { key: 'documents', label: '文件管理', icon: FolderTree, planned: false },
  { key: 'retrieve', label: '检索测试', icon: Search, planned: false },
  { key: 'graph', label: '知识图谱', icon: Share2, planned: true },
  { key: 'mindmap', label: '知识导图', icon: GitBranch, planned: true },
  { key: 'eval', label: 'RAG 评估', icon: BarChart3, planned: true },
  { key: 'benchmark', label: '评估基准', icon: Target, planned: true },
]

interface Props {
  /** 当前选中的 Tab key */
  modelValue: string
}
const props = defineProps<Props>()

interface Emits {
  (e: 'update:modelValue', key: string): void
  (e: 'select', key: string): void
}
const emit = defineEmits<Emits>()

const activeKey = computed(() => props.modelValue)

function handleClick(tab: TabItem): void {
  emit('select', tab.key)
  if (!tab.planned) {
    emit('update:modelValue', tab.key)
  }
}
</script>

<template>
  <nav class="kb-tabs">
    <button
      v-for="tab in TABS"
      :key="tab.key"
      type="button"
      class="kb-tabs__item"
      :class="{
        'kb-tabs__item--active': activeKey === tab.key,
        'kb-tabs__item--planned': tab.planned,
      }"
      @click="handleClick(tab)"
    >
      <component :is="tab.icon" :size="15" class="kb-tabs__icon" />
      <span class="kb-tabs__label">{{ tab.label }}</span>
      <span v-if="tab.planned" class="kb-tabs__planned-tag">规划中</span>
    </button>
  </nav>
</template>

<style scoped>
.kb-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 24px;
  background-color: var(--kb-card-bg);
  border-bottom: 1px solid var(--kb-border);
  overflow-x: auto;
}

.kb-tabs__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--kb-text-secondary);
  transition: color 0.15s;
  white-space: nowrap;
  user-select: none;
}

.kb-tabs__item:hover {
  color: var(--kb-primary);
}

.kb-tabs__item--active {
  color: var(--kb-primary);
  font-weight: 500;
}

.kb-tabs__item--active::after {
  content: '';
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: -1px;
  height: 2px;
  background-color: var(--kb-primary);
  border-radius: 2px;
}

.kb-tabs__item--planned {
  color: var(--kb-text-tertiary);
}

.kb-tabs__item--planned:hover {
  color: var(--kb-text-secondary);
}

.kb-tabs__icon {
  flex-shrink: 0;
}

.kb-tabs__label {
  line-height: 1;
}

.kb-tabs__planned-tag {
  margin-left: 2px;
  padding: 1px 6px;
  font-size: 11px;
  line-height: 1.4;
  border-radius: 8px;
  color: var(--kb-text-tertiary);
  background-color: #f3f4f6;
  border: 1px solid var(--kb-border);
}
</style>
