<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式见 web/src/assets/styles/yuxi/components.css。
-->
<script setup lang="ts">
/**
 * Yuxi 风格空状态。
 * 支持 title / description / actions 插槽与图标。
 */
import { computed, type FunctionalComponent } from 'vue'
import { Inbox, type LucideProps } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    /** 标题（必填） */
    title: string
    /** 描述文案 */
    description?: string
    /** 图标组件，默认 Inbox */
    icon?: FunctionalComponent<LucideProps> | Component
    /** 尺寸变体 */
    size?: 'default' | 'compact'
    /** 是否撑满父容器高度 */
    fullHeight?: boolean
  }>(),
  {
    size: 'default',
    fullHeight: false
  }
)

type Component = FunctionalComponent<LucideProps>

const iconComp = computed(() => props.icon ?? Inbox)
const iconSize = computed(() => (props.size === 'compact' ? 22 : 24))
</script>

<template>
  <div
    class="yuxi-empty-state"
    :class="{
      'yuxi-empty-state--compact': props.size === 'compact',
      'yuxi-empty-state--full-height': props.fullHeight
    }"
  >
    <div class="yuxi-empty-state__icon">
      <component :is="iconComp" :size="iconSize" :stroke-width="1.8" />
    </div>
    <h3 class="yuxi-empty-state__title">{{ props.title }}</h3>
    <p v-if="props.description" class="yuxi-empty-state__description">{{ props.description }}</p>
    <div v-if="$slots.action || $slots.actions" class="yuxi-empty-state__actions">
      <slot name="action" />
      <slot name="actions" />
    </div>
  </div>
</template>
