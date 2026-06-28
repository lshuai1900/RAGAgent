<script setup lang="ts">
/**
 * 顶部标题区：展示当前页面标题
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const title = computed(() => (route.meta.title as string | undefined) ?? 'RAGAgent 控制台')
</script>

<template>
  <header class="app-header">
    <h1 class="app-header__title">{{ title }}</h1>
  </header>
</template>

<style scoped>
.app-header {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background-color: var(--app-header-bg);
  border-bottom: 1px solid var(--app-border);
}

.app-header__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--app-text);
}
</style>
