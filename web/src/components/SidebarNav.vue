<script setup lang="ts">
/**
 * 左侧导航栏：中文菜单
 * - 仪表盘  /dashboard
 * - 知识库  /knowledge-bases
 * - 聊天问答 /chat
 * - 设置    /settings
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Library, MessageSquareText, Settings } from 'lucide-vue-next'

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
      <span class="sidebar__brand-title">RAGAgent 控制台</span>
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
  </nav>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar__brand {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--app-border);
  font-weight: 600;
  font-size: 15px;
  color: var(--app-text);
}

.sidebar__menu {
  list-style: none;
  margin: 0;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--app-radius);
  cursor: pointer;
  color: var(--app-text-secondary);
  transition: background-color 0.15s, color 0.15s;
  user-select: none;
}

.sidebar__item:hover {
  background-color: #fafafa;
  color: var(--app-text);
}

.sidebar__item--active {
  background-color: #e6f4ff;
  color: #1677ff;
}

.sidebar__icon {
  flex-shrink: 0;
}

.sidebar__label {
  font-size: 14px;
}
</style>
