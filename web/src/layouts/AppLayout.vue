<script setup lang="ts">
/**
 * 全局布局
 * - 默认：左侧导航栏 + 顶部标题区 + 主内容区（工程控制台风格）
 * - 沉浸式（route.meta.immersive = true）：隐藏左侧菜单与顶部标题栏，
 *   仅渲染主内容区，供知识库详情页等沉浸式工作台使用（P1.6 / Yuxi 风格）
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SidebarNav from '@/components/SidebarNav.vue'
import AppHeader from '@/components/AppHeader.vue'

const route = useRoute()
const immersive = computed(() => route.meta.immersive === true)
</script>

<template>
  <!-- 沉浸式布局：仅主内容区，由详情页自带 Header 与 Tab -->
  <div v-if="immersive" class="app-layout app-layout--immersive">
    <main class="app-layout__immersive-content">
      <router-view />
    </main>
  </div>

  <!-- 默认布局：左侧菜单 + 顶部标题 + 主内容 -->
  <div v-else class="app-layout">
    <aside class="app-layout__sidebar">
      <SidebarNav />
    </aside>
    <div class="app-layout__main">
      <AppHeader />
      <main class="app-layout__content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  background-color: var(--app-bg);
}

.app-layout__sidebar {
  width: 220px;
  flex-shrink: 0;
  background-color: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-border);
  overflow-y: auto;
}

.app-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-layout__content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

/* 沉浸式布局：满屏主内容，由详情页自行管理背景与滚动 */
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
