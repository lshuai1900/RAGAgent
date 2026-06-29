<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式见 web/src/assets/styles/yuxi/layout.css。
-->
<script setup lang="ts">
/**
 * Yuxi 风格应用外壳：侧栏 + 主内容区。
 *
 * 仅保留 RAG-only 允许的导航项：仪表盘 / 知识库 / 聊天问答 / 设置。
 * 不渲染登录 / 用户信息 / 租户切换 / 任务中心 / 会话历史 /
 * Agent / MCP / Skills / SubAgents / Sandbox / Knowledge Graph / Evaluation 等入口。
 * 暂缓项通过 web/src/config/features.ts 的 featureFlags 默认 false 控制。
 */
import { computed, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { PanelLeftClose, PanelLeftOpen, Boxes, MessageSquare, Settings } from 'lucide-vue-next'
import { Library } from 'lucide-vue-next'
import { featureFlags } from '@/config/features'

interface NavItem {
  /** 路由路径 */
  path: string
  /** 显示文案 */
  label: string
  /** 图标组件 */
  icon: unknown
  /** 路由匹配模式：exact 精确匹配，prefix 前缀匹配 */
  match?: 'exact' | 'prefix'
}

const props = withDefaults(
  defineProps<{
    /** 沉浸式模式（隐藏侧栏与品牌区，详情页用） */
    immersive?: boolean
    /** 初始折叠状态 */
    defaultCollapsed?: boolean
  }>(),
  {
    immersive: false,
    defaultCollapsed: false
  }
)

const route = useRoute()
const router = useRouter()

/** 折叠状态：沉浸式或移动端强制折叠，由本地 ref 管理 */
const collapsed = ref(props.defaultCollapsed || props.immersive)

watch(
  () => props.immersive,
  (val) => {
    collapsed.value = val || props.defaultCollapsed
  }
)

function toggleSidebar() {
  collapsed.value = !collapsed.value
}

/** 导航项列表，全部暂缓项已剔除，不依赖 featureFlags（默认 false） */
const navItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [
    { path: '/', label: '仪表盘', icon: Boxes, match: 'exact' },
    { path: '/knowledge-bases', label: '知识库', icon: Library, match: 'prefix' },
    { path: '/chat', label: '聊天问答', icon: MessageSquare, match: 'prefix' },
    { path: '/settings', label: '设置', icon: Settings, match: 'exact' }
  ]
  // 预留：未来通过 featureFlags 开启的导航项在此追加。
  void featureFlags
  return items
})

function isActive(item: NavItem): boolean {
  const mode = item.match ?? 'prefix'
  if (mode === 'exact') {
    return route.path === item.path
  }
  if (item.path === '/') {
    return route.path === '/'
  }
  return route.path === item.path || route.path.startsWith(`${item.path}/`)
}

function go(path: string) {
  void router.push(path)
}
</script>

<template>
  <div
    class="yuxi-app-shell"
    :class="{
      'yuxi-app-shell--immersive': immersive,
      'yuxi-app-shell--collapsed': collapsed && !immersive
    }"
  >
    <aside
      v-if="!immersive"
      class="yuxi-app-shell__sidebar"
      :class="{ 'yuxi-app-shell__sidebar--collapsed': collapsed }"
    >
      <!-- 品牌区 -->
      <div class="yuxi-app-shell__brand">
        <RouterLink v-if="!collapsed" to="/" class="yuxi-app-shell__brand-link">
          <span class="yuxi-app-shell__brand-avatar">
            <Boxes :size="18" />
          </span>
          <span class="yuxi-app-shell__brand-text">
            <span class="yuxi-app-shell__brand-name">RAGAgent</span>
            <span class="yuxi-app-shell__brand-subtitle">轻量 RAG 工作台</span>
          </span>
        </RouterLink>
        <button
          v-else
          type="button"
          class="yuxi-app-shell__brand-link"
          aria-label="展开侧边栏"
          @click="toggleSidebar"
        >
          <span class="yuxi-app-shell__brand-avatar">
            <Boxes :size="18" />
          </span>
        </button>
        <button
          v-if="!collapsed"
          type="button"
          class="yuxi-app-shell__toggle"
          aria-label="折叠侧边栏"
          @click="toggleSidebar"
        >
          <PanelLeftClose :size="18" />
        </button>
      </div>

      <!-- 导航列表 -->
      <nav class="yuxi-app-shell__nav" aria-label="主导航">
        <a
          v-for="item in navItems"
          :key="item.path"
          class="yuxi-app-shell__item"
          :class="{ 'yuxi-app-shell__item--active': isActive(item) }"
          href="javascript:void(0)"
          @click="go(item.path)"
        >
          <component :is="item.icon" class="yuxi-app-shell__item-icon" :size="16" />
          <span class="yuxi-app-shell__item-label">{{ item.label }}</span>
        </a>
      </nav>

      <div class="yuxi-app-shell__fill" />

      <!-- 底部：无任何暂缓入口，仅保留展开按钮（折叠态） -->
      <div class="yuxi-app-shell__footer">
        <button
          v-if="collapsed"
          type="button"
          class="yuxi-app-shell__toggle"
          style="width: 100%"
          aria-label="展开侧边栏"
          @click="toggleSidebar"
        >
          <PanelLeftOpen :size="18" />
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="yuxi-app-shell__content">
      <RouterView />
    </main>
  </div>
</template>
