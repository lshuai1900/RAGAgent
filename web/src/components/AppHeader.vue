<script setup lang="ts">
/**
 * 顶部标题区（P1.8 / Yuxi 风格）
 * - 展示当前页面标题 + 副标题（来自 route.meta）
 * - 白色背景 + 细底边
 * - 不再像后台管理系统的强顶部栏
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const title = computed(() => (route.meta.title as string | undefined) ?? 'RAGAgent')

/** 副标题映射（轻量产品工作台风格） */
const subtitle = computed<string>(() => {
  switch (route.name) {
    case 'dashboard':
      return '查看后端服务与依赖组件状态'
    case 'knowledgeBaseList':
      return '管理用于 RAG 问答的知识库'
    case 'chat':
      return '选择知识库后进行流式问答'
    case 'settings':
      return '配置后端 API 地址'
    default:
      return ''
  }
})
</script>

<template>
  <header class="app-header">
    <div class="app-header__main">
      <h1 class="app-header__title">{{ title }}</h1>
      <span v-if="subtitle" class="app-header__subtitle">{{ subtitle }}</span>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 0 28px;
  background-color: var(--kb-surface);
  border-bottom: 1px solid var(--kb-border);
}

.app-header__main {
  display: flex;
  align-items: baseline;
  gap: 12px;
  min-width: 0;
}

.app-header__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--kb-text);
}

.app-header__subtitle {
  font-size: 13px;
  color: var(--kb-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
