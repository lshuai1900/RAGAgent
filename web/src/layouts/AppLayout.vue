<script setup lang="ts">
/**
 * 全局布局（Yuxi 风格 1:1 复刻）
 * - 默认：左侧导航栏（230px，可折叠 56px）+ 主内容区，无独立顶部 Header
 * - 沉浸式（route.meta.immersive = true）：满屏主内容，由详情页自带 top-bar + 横向 Tab
 *
 * 视觉规格（参考 Yuxi AppLayout，不复制源码）：
 * - 整体 flex row，height:100vh，min-width:400px
 * - 侧边栏：背景 #fcfefe，右边框 1px solid #eff2f2
 * - 主内容：flex:1，overflow-y:auto，无固定 padding（由各页面 PageHeader 自带 --page-padding）
 */
import { computed, ref, provide, readonly } from 'vue'
import { useRoute } from 'vue-router'
import SidebarNav from '@/components/SidebarNav.vue'

const route = useRoute()
const immersive = computed(() => route.meta.immersive === true)

/** 侧边栏折叠状态（提供给 SidebarNav 双向绑定） */
const collapsed = ref<boolean>(false)

function toggleCollapsed(): void {
  collapsed.value = !collapsed.value
}

provide('appLayoutCollapsed', readonly(collapsed))
provide('appLayoutToggleCollapsed', toggleCollapsed)
</script>

<template>
  <!-- 沉浸式布局：满屏主内容，由详情页自行管理 top-bar 与横向 Tab -->
  <div v-if="immersive" class="app-layout app-layout--immersive">
    <main class="app-layout__immersive-content">
      <router-view />
    </main>
  </div>

  <!-- 默认布局：侧边栏 + 主内容（无独立顶部 Header） -->
  <div v-else class="app-layout">
    <aside class="app-layout__sidebar" :class="{ 'app-layout__sidebar--collapsed': collapsed }">
      <SidebarNav />
    </aside>
    <main class="app-layout__content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  min-width: 400px;
  background-color: var(--kb-bg);
}

.app-layout__sidebar {
  width: 230px;
  flex-shrink: 0;
  background-color: var(--kb-primary-sidebar);
  border-right: 1px solid var(--kb-border-light);
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.18s ease;
}

.app-layout__sidebar--collapsed {
  width: 56px;
}

.app-layout__content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 沉浸式布局：满屏主内容 */
.app-layout--immersive {
  background-color: var(--kb-bg);
}

.app-layout__immersive-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
</style>
