<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式见 web/src/assets/styles/yuxi/components.css。
-->
<script setup lang="ts">
/**
 * Yuxi 风格卡片容器。
 * 支持 title / description / icon / extra slot / default slot / footer slot。
 */
import { computed, type FunctionalComponent } from 'vue'
import { type LucideProps } from 'lucide-vue-next'

const props = withDefaults(
  defineProps<{
    /** 卡片标题 */
    title?: string
    /** 描述文案 */
    description?: string
    /** 图标组件 */
    icon?: FunctionalComponent<LucideProps>
    /** 是否可交互（hover 高亮 + pointer） */
    interactive?: boolean
    /** 是否扁平背景（去掉渐变） */
    flat?: boolean
    /** 点击事件（仅在 interactive=true 时有意义） */
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  }>(),
  {
    interactive: false,
    flat: false
  }
)

const cardClass = computed(() => [
  'yuxi-card',
  {
    'yuxi-card--interactive': props.interactive,
    'yuxi-card--flat': props.flat
  }
])
</script>

<template>
  <div :class="cardClass">
    <div v-if="props.title || props.icon || $slots.extra" class="yuxi-card__header">
      <div v-if="props.icon" class="yuxi-card__icon">
        <component :is="props.icon" :size="20" />
      </div>
      <div v-if="props.title || props.description" class="yuxi-card__info">
        <span v-if="props.title" class="yuxi-card__title">{{ props.title }}</span>
        <span v-if="props.description" class="yuxi-card__description">{{ props.description }}</span>
      </div>
      <div v-if="$slots.extra" class="yuxi-card__extra">
        <slot name="extra" />
      </div>
    </div>
    <div v-if="$slots.default" class="yuxi-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="yuxi-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>
