<script setup lang="ts">
/**
 * 404 页面
 */
import { useRouter } from 'vue-router'
import { Button, Empty } from 'ant-design-vue'

const router = useRouter()

function goHome(): void {
  router.push('/dashboard')
}
</script>

<template>
  <div class="not-found">
    <Empty description="页面未找到">
      <Button type="primary" @click="goHome">返回首页</Button>
    </Empty>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}
</style>
