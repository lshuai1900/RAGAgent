<script setup lang="ts">
/**
 * 全局布局：左侧导航栏 + 顶部标题区 + 主内容区
 * 工程控制台风格：浅色背景、细边框、卡片式内容区
 */
import SidebarNav from '@/components/SidebarNav.vue'
import AppHeader from '@/components/AppHeader.vue'
</script>

<template>
  <div class="app-layout">
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
</style>
