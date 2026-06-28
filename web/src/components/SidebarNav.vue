<script setup lang="ts">
/**
 * 左侧导航栏（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi Sidebar，不复制源码）：
 * - 背景 #fcfefe，右边框 1px solid #eff2f2
 * - 内边距 6px 8px，纵向 gap 16px
 * - 品牌区：28×28 头像 + 组织名（15px/650/#151616）+ 折叠按钮（32×32，hover 边框 #e1f6fb + 底 #f6f9fa + 主色字）
 * - 导航项：高 36px，圆角 8px，左右内边距 10px，字号 14px/450，默认色 #4c4d4d
 *   hover：底 #f6f9fa，文字主色 #046a82
 *   active：底 color-mix(主色 6%, 白)，文字主色 #046a82，字重 600
 *   折叠态：仅显示图标，文字 max-width:0; opacity:0
 * - 底部：GitHub 入口 + 用户信息
 */
import { computed, inject, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  Library,
  MessageSquareText,
  Settings as SettingsIcon,
  Database,
  PanelLeftClose,
  PanelLeftOpen,
  Github,
} from 'lucide-vue-next'

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
  { key: 'settings', label: '设置', path: '/settings', icon: SettingsIcon },
]

const route = useRoute()
const router = useRouter()

/** 从 AppLayout 注入的折叠状态 */
const collapsed = inject<import('vue').Ref<boolean>>('appLayoutCollapsed', ref(false))
const toggleCollapsed = inject<() => void>('appLayoutToggleCollapsed', () => {})

/** 当前选中项（按路径前缀匹配） */
const selectedKey = computed(() => {
  const path = route.path
  const matched = menuItems
    .filter((item) => path === item.path || path.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return matched?.key ?? 'dashboard'
})

function handleClick(item: MenuItem): void {
  if (route.path !== item.path) {
    router.push(item.path)
  }
}
</script>

<template>
  <nav class="sidebar" :class="{ 'sidebar--collapsed': collapsed }">
    <!-- 品牌区 -->
    <div class="sidebar__brand">
      <div class="sidebar__brand-avatar">
        <Database :size="16" />
      </div>
      <span class="sidebar__brand-name">RAGAgent</span>
      <button
        type="button"
        class="sidebar__collapse-btn"
        :title="collapsed ? '展开侧边栏' : '折叠侧边栏'"
        @click="toggleCollapsed"
      >
        <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" :size="16" />
      </button>
    </div>

    <!-- 导航列表 -->
    <ul class="sidebar__nav">
      <li
        v-for="item in menuItems"
        :key="item.key"
        class="sidebar__item"
        :class="{ 'sidebar__item--active': selectedKey === item.key }"
        :title="collapsed ? item.label : undefined"
        @click="handleClick(item)"
      >
        <component :is="item.icon" class="sidebar__item-icon" :size="16" />
        <span class="sidebar__item-label">{{ item.label }}</span>
      </li>
    </ul>

    <!-- 填充区 -->
    <div class="sidebar__fill" />

    <!-- 底部 -->
    <div class="sidebar__footer">
      <a
        class="sidebar__footer-link"
        href="https://github.com/xerrors/Yuxi"
        target="_blank"
        rel="noopener noreferrer"
        :title="collapsed ? 'Yuxi（UI 参考）' : undefined"
      >
        <Github :size="16" class="sidebar__footer-icon" />
        <span class="sidebar__footer-text">UI 参考自 Yuxi</span>
      </a>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 6px 8px;
  gap: 16px;
  background-color: transparent;
}

/* ===== 品牌区 ===== */
.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px 6px 2px;
  min-height: 40px;
}

.sidebar__brand-avatar {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary);
  color: #ffffff;
  flex-shrink: 0;
}

.sidebar__brand-name {
  font-size: 15px;
  font-weight: 650;
  color: var(--kb-text-strong);
  letter-spacing: 0.2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  transition: opacity 0.18s ease;
}

.sidebar__collapse-btn {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--kb-text-tertiary);
  cursor: pointer;
  transition: background-color 0.18s ease, border-color 0.18s ease, color 0.18s ease;
}

.sidebar__collapse-btn:hover {
  border-color: var(--kb-primary-soft-hover);
  background-color: var(--kb-primary-bg-hover);
  color: var(--kb-primary-hover);
}

/* ===== 导航列表 ===== */
.sidebar__nav {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar__item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--kb-text-secondary);
  font-size: 14px;
  font-weight: 450;
  transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar__item:hover {
  background-color: var(--kb-primary-bg-hover);
  color: var(--kb-primary-hover);
}

.sidebar__item--active {
  background-color: rgba(36, 131, 154, 0.06);
  color: var(--kb-primary-hover);
  font-weight: 600;
}

.sidebar__item-icon {
  flex-shrink: 0;
}

.sidebar__item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.18s ease, max-width 0.18s ease;
  max-width: 200px;
}

/* ===== 填充区 ===== */
.sidebar__fill {
  flex: 1;
}

/* ===== 底部 ===== */
.sidebar__footer {
  padding: 4px 0;
  border-top: 1px solid var(--kb-border-light);
  margin-top: 4px;
}

.sidebar__footer-link {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  color: var(--kb-text-tertiary);
  font-size: 13px;
  transition: background-color 0.2s ease, color 0.2s ease;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar__footer-link:hover {
  background-color: var(--kb-primary-bg-hover);
  color: var(--kb-primary-hover);
}

.sidebar__footer-icon {
  flex-shrink: 0;
}

.sidebar__footer-text {
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.18s ease, max-width 0.18s ease;
  max-width: 200px;
}

/* ===== 折叠态 ===== */
.sidebar--collapsed .sidebar__brand-name,
.sidebar--collapsed .sidebar__item-label,
.sidebar--collapsed .sidebar__footer-text {
  opacity: 0;
  max-width: 0;
}

.sidebar--collapsed .sidebar__brand {
  justify-content: center;
  padding: 6px 0;
}

.sidebar--collapsed .sidebar__item,
.sidebar--collapsed .sidebar__footer-link {
  justify-content: center;
  padding: 0;
}

.sidebar--collapsed .sidebar__collapse-btn {
  width: 28px;
  height: 28px;
}
</style>
