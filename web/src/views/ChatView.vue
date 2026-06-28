<script setup lang="ts">
/**
 * 聊天问答页（P1.1 占位）
 * SSE 流式问答将在 P1.4 实现
 */
import { Card, Empty } from 'ant-design-vue'
</script>

<template>
  <div class="chat-view">
    <Card class="chat-view__card" :bordered="true">
      <template #title>聊天问答</template>
      <Empty description="聊天问答将在后续批次实现" />
    </Card>
  </div>
</template>

<style scoped>
.chat-view {
  max-width: 1200px;
}

.chat-view__card {
  border-radius: var(--app-radius);
}
</style>
