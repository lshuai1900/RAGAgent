<script setup lang="ts">
/**
 * 知识库详情页横向 Tab 导航（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi database-tab-bar，不复制源码）：
 * - tab-bar：padding:8px 12px 0，底边框 1px solid #eef0f0，白底，overflow-x:auto
 * - tab-list：flex，gap:6px，min-width:max-content
 * - tab-item：min-height:40px，圆角 8px 8px 0 0，无边框，透明底
 *   内边距 0 14px 8px，gap:10px，图标 17px + 文字
 *   字号 14px/500，默认色 #697070
 *   hover：色 #1e1f1f，底 #f5f7f7
 *   active：色主色 #046a82，底 #f6f9fa
 *   底部下划线 ::before：left/right:12px, bottom:0, height:3px, border-radius:3px 3px 0 0, background:主色
 *   过渡 background 0.15s, color 0.15s
 *
 * 6 个 Tab：文件管理 / 检索测试 / 知识图谱 / 知识导图 / RAG 评估 / 评估基准
 * - 文件管理 / 检索测试：真实功能
 * - 其余：规划中，Tab 上显示"规划中"小标签，点击不切换，由父组件提示
 */
import { computed } from 'vue'
import {
  FileText,
  Search,
  Network,
  Map,
  BarChart3,
  ClipboardList,
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
  { key: 'documents', label: '文件管理', icon: FileText, planned: false },
  { key: 'retrieve', label: '检索测试', icon: Search, planned: false },
  { key: 'graph', label: '知识图谱', icon: Network, planned: true },
  { key: 'mindmap', label: '知识导图', icon: Map, planned: true },
  { key: 'eval', label: 'RAG 评估', icon: BarChart3, planned: true },
  { key: 'benchmark', label: '评估基准', icon: ClipboardList, planned: true },
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
  <div class="kb-tabs">
    <nav class="kb-tabs__list" role="tablist" aria-label="知识库功能标签">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        type="button"
        class="kb-tabs__item"
        :class="{
          'kb-tabs__item--active': activeKey === tab.key,
          'kb-tabs__item--planned': tab.planned,
        }"
        role="tab"
        :aria-selected="activeKey === tab.key"
        @click="handleClick(tab)"
      >
        <component :is="tab.icon" :size="17" class="kb-tabs__icon" />
        <span class="kb-tabs__label">{{ tab.label }}</span>
        <span v-if="tab.planned" class="kb-tabs__planned-tag">规划中</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.kb-tabs {
  padding: 8px 12px 0;
  background-color: var(--kb-surface);
  border-bottom: 1px solid var(--kb-border);
  overflow-x: auto;
  flex-shrink: 0;
}

.kb-tabs__list {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  min-width: max-content;
}

.kb-tabs__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 14px 8px;
  background: transparent;
  border: none;
  border-radius: var(--kb-radius) var(--kb-radius) 0 0;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--kb-text-tertiary);
  transition: background-color 0.15s ease, color 0.15s ease;
  white-space: nowrap;
  user-select: none;
}

.kb-tabs__item:hover {
  color: var(--kb-text-title);
  background-color: var(--kb-bg-hover);
}

.kb-tabs__item--active {
  color: var(--kb-primary-hover);
  background-color: var(--kb-primary-bg-hover);
}

/* 底部下划线（3px 主色） */
.kb-tabs__item--active::before {
  content: '';
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 0;
  height: 3px;
  border-radius: 3px 3px 0 0;
  background-color: var(--kb-primary);
}

.kb-tabs__item--planned {
  color: var(--kb-text-quaternary);
}

.kb-tabs__item--planned:hover {
  color: var(--kb-text-tertiary);
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
  font-weight: 500;
  border-radius: var(--kb-radius-pill);
  color: var(--kb-text-quaternary);
  background-color: var(--kb-bg-soft);
  border: 1px solid var(--kb-border);
}
</style>
