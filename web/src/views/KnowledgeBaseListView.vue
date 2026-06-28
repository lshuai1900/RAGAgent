<script setup lang="ts">
/**
 * 知识库列表页（P1.1 占位）
 * 真实列表与新建功能将在 P1.2 实现
 */
import { Card, Empty } from 'ant-design-vue'
</script>

<template>
  <div class="kb-list">
    <Card class="kb-list__card" :bordered="true">
      <template #title>知识库</template>
      <Empty description="知识库列表将在下一批实现" />
    </Card>
  </div>
</template>

<style scoped>
.kb-list {
  max-width: 1200px;
}

.kb-list__card {
  border-radius: var(--app-radius);
}
</style>
