<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式见 web/src/assets/styles/yuxi/components.css。
-->
<script setup lang="ts">
/**
 * Yuxi 风格状态徽标。
 * 用于知识库状态 / 文档状态 / 健康检查状态展示。
 */
import { computed } from 'vue'
import type { Component } from 'vue'
import { CheckCircle2, Loader2, AlertCircle, XCircle, Circle } from 'lucide-vue-next'

export type YuxiStatusKind = 'success' | 'processing' | 'warning' | 'error' | 'default'

const props = withDefaults(
  defineProps<{
    /** 状态种类 */
    kind?: YuxiStatusKind
    /** 自定义文案，未传则使用 kind 的默认中文文案 */
    label?: string
    /** 是否显示状态点 */
    dot?: boolean
  }>(),
  {
    kind: 'default',
    dot: true
  }
)

const defaultLabels: Record<YuxiStatusKind, string> = {
  success: '就绪',
  processing: '处理中',
  warning: '警告',
  error: '失败',
  default: '未知'
}

const iconMap: Record<YuxiStatusKind, Component> = {
  success: CheckCircle2,
  processing: Loader2,
  warning: AlertCircle,
  error: XCircle,
  default: Circle
}

const currentLabel = computed(() => props.label ?? defaultLabels[props.kind])
const currentIcon = computed(() => iconMap[props.kind])
const isProcessing = computed(() => props.kind === 'processing')
</script>

<template>
  <span class="yuxi-status-badge" :class="`yuxi-status-badge--${props.kind}`">
    <span v-if="props.dot" class="yuxi-status-badge__dot" />
    <component
      :is="currentIcon"
      v-if="!props.dot"
      :size="12"
      :class="{ 'yuxi-status-badge__icon--spin': isProcessing }"
    />
    {{ currentLabel }}
  </span>
</template>

<style scoped>
.yuxi-status-badge__icon--spin {
  animation: yuxi-status-badge-spin 1s linear infinite;
}
@keyframes yuxi-status-badge-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
