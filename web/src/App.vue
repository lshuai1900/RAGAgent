<script setup lang="ts">
/**
 * 根组件：渲染 Yuxi 风格应用外壳。
 * immersive 由路由 meta 控制（详情页满屏，隐藏侧栏）。
 *
 * Antd ConfigProvider 最小主题对齐：primary 色设为 Yuxi 青蓝色（#046a82），
 * 与 --yuxi-main-700 保持一致。不引入新主题系统。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { ConfigProvider } from 'ant-design-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import YuxiAppShell from '@/components/yuxi/YuxiAppShell.vue'

const route = useRoute()
const immersive = computed(() => route.meta.immersive === true)

/** Antd 主题 token：primary 对齐 Yuxi 青蓝色 */
const themeConfig = {
  token: {
    colorPrimary: '#046a82',
    borderRadius: 8
  }
}
</script>

<template>
  <ConfigProvider :locale="zhCN" :theme="themeConfig">
    <YuxiAppShell :immersive="immersive" />
  </ConfigProvider>
</template>
