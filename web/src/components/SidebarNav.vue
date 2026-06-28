<script setup lang="ts">
/**
 * 左侧导航栏（P1.8 / Yuxi 风格）
 * - 轻量产品导航：仪表盘 / 知识库 / 聊天问答 / 设置
 * - 顶部品牌区使用蓝绿色主色徽标
 * - 选中项使用主色 soft 背景 + 主色文字 + 左侧高亮条
 * - hover 浅灰背景，无重阴影
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Library, MessageSquareText, Settings, Database } from 'lucide-vue-next'

interface MenuItem {
  key: string
  label: string
  path: string
  icon: unknown
}

const menuItems: MenuItem[] = [
  { key: 'dashboard', label: '仪表盘', path: '/dashboard', icon: LayoutDashboard },
  { key: 'knowledge-bases', label: '知识库', path: '/knowledge-bases', icon: Library },
  { key: 'chat', label: '聊天问答', path: '/chat', icon: MessageSquareText },
  { key: 'settings', label: '设置', path: '/settings', icon: Settings },
]

const route = useRoute()
const router = useRouter()

/** 当前选中项（按路径前缀匹配） */
const selectedKey = computed(() => {
  const path = route.path
  const matched = menuItems
    .filter((item) => path === item.path || path.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return matched?.key ?? 'dashboard'
})

function handleClick(item: MenuItem): void {
  router.push(item.path)
}
</script>

<template>
  <nav class="sidebar">
    <div class="sidebar__brand">
      <span class="sidebar__brand-badge">
        <Database :size="16" />
      </span>
      <span class="sidebar__brand-title">RAGAgent</span>
      <span class="sidebar__brand-subtitle">知识库工作台</span>
    </div>
    <ul class="sidebar__menu">
      <li
        v-for="item in menuItems"
        :key="item.key"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': selectedKey === item.key }"
        @click="handleClick(item)"
      >
        <component :is="item.icon" class="sidebar__icon" :size="16" />
        <span class="sidebar__label">{{ item.label }}</span>
      </li>
    </ul>
    <div class="sidebar__footer">
      <span class="sidebar__footer-text">基于 RAG 的知识库产品</span>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--kb-surface);
}

.sidebar__brand {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  border-bottom: 1px solid var(--kb-border-light);
}

.sidebar__brand-badge {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary);
  color: #ffffff;
  flex-shrink: 0;
}

.sidebar__brand-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--kb-text);
  letter-spacing: 0.2px;
}

.sidebar__brand-subtitle {
  margin-left: auto;
  font-size: 11px;
  color: var(--kb-text-tertiary);
}

.sidebar__menu {
  list-style: none;
  margin: 0;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.sidebar__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--kb-text-secondary);
  transition: background-color 0.15s, color 0.15s;
  user-select: none;
}

.sidebar__item:hover {
  background-color: var(--kb-bg);
  color: var(--kb-text);
}

.sidebar__item--active {
  background-color: var(--kb-primary-soft);
  color: var(--kb-primary);
  font-weight: 500;
}

.sidebar__item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 2px 2px 0;
  background-color: var(--kb-primary);
}

.sidebar__icon {
  flex-shrink: 0;
}

.sidebar__label {
  font-size: 14px;
}

.sidebar__footer {
  padding: 12px 18px;
  border-top: 1px solid var(--kb-border-light);
}

.sidebar__footer-text {
  font-size: 11px;
  color: var(--kb-text-tertiary);
}
</style>
