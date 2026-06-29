<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式参考 Yuxi database-tab-bar，改写为 plain CSS。
  仅保留 RAG-only 允许的 3 个 Tab，删除知识图谱/导图/评估等暂缓入口。
-->
<script setup lang="ts">
/**
 * 知识库详情页横向 Tab 导航（Yuxi 风格）
 *
 * 仅 3 个真实功能 Tab：文件管理 / 检索测试 / 聊天问答。
 * 通过 RouterLink 跳转子路由，active 状态由路由匹配自动判定。
 * 不渲染任何 planned / 暂缓 Tab（知识图谱 / 导图 / 评估 / 模型配置 / 权限等）。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { FileText, Search, MessageSquare } from 'lucide-vue-next'
import { featureFlags } from '@/config/features'

interface TabItem {
  /** 路由 name */
  to: string
  /** 子路由路径片段（files/retrieval/chat） */
  tab: string
  /** 显示文案 */
  label: string
  /** 图标 */
  icon: unknown
}

const route = useRoute()

const baseTabs: TabItem[] = [
  { to: 'knowledgeBaseFiles', tab: 'files', label: '文件管理', icon: FileText },
  { to: 'knowledgeBaseRetrieval', tab: 'retrieval', label: '检索测试', icon: Search },
  { to: 'knowledgeBaseChat', tab: 'chat', label: '聊天问答', icon: MessageSquare },
]

/** Tab 列表：默认仅 3 个真实 Tab；暂缓项由 featureFlags 控制（默认 false，不渲染） */
const tabs = computed<TabItem[]>(() => {
  // 预留：未来通过 featureFlags 开启的 Tab 在此追加。
  // 当前 ENABLE_PLANNED_TABS = false，不渲染任何暂缓入口。
  void featureFlags
  return baseTabs
})

function isActive(tab: TabItem): boolean {
  return route.meta.tab === tab.tab
}
</script>

<template>
  <nav class="kb-tabs" role="tablist" aria-label="知识库功能标签">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.tab"
      :to="{ name: tab.to, params: { kbId: route.params.kbId } }"
      class="kb-tabs__item"
      :class="{ 'kb-tabs__item--active': isActive(tab) }"
      role="tab"
      :aria-selected="isActive(tab)"
    >
      <component :is="tab.icon" :size="17" class="kb-tabs__icon" />
      <span class="kb-tabs__label">{{ tab.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.kb-tabs {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  padding: 8px var(--kb-page-padding, 24px) 0;
  background-color: var(--yuxi-gray-0);
  border-bottom: 1px solid var(--yuxi-gray-100);
  overflow-x: auto;
  flex-shrink: 0;
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
  border-radius: var(--yuxi-radius) var(--yuxi-radius) 0 0;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--yuxi-gray-600);
  text-decoration: none;
  transition: background-color 0.15s ease, color 0.15s ease;
  white-space: nowrap;
  user-select: none;
}

.kb-tabs__item:hover {
  color: var(--yuxi-gray-900);
  background-color: var(--yuxi-gray-50);
}

.kb-tabs__item--active {
  color: var(--yuxi-main-color);
  background-color: var(--yuxi-main-20);
  font-weight: 600;
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
  background-color: var(--yuxi-main-color);
}

.kb-tabs__icon {
  flex-shrink: 0;
}

.kb-tabs__label {
  line-height: 1;
}
</style>
