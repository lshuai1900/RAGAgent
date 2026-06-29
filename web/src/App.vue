<script setup lang="ts">
/**
 * 根组件：渲染 Yuxi 风格应用外壳。
 * immersive 由路由 meta 控制（详情页满屏，隐藏侧栏）。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import YuxiAppShell from '@/components/yuxi/YuxiAppShell.vue'

const route = useRoute()
const immersive = computed(() => route.meta.immersive === true)
</script>

<template>
  <YuxiAppShell :immersive="immersive" />
</template>
