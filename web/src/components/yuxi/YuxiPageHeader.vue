<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  组件样式见 web/src/assets/styles/yuxi/components.css。
-->
<script setup lang="ts">
/**
 * Yuxi 风格页头。
 * 支持 title / description / back 按钮 / extra slot。
 */
import { ArrowLeft } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    /** 页面标题 */
    title: string
    /** 描述文案 */
    description?: string
    /** 是否显示返回按钮（默认不显示） */
    showBack?: boolean
    /** 是否显示底部边框 */
    bordered?: boolean
  }>(),
  {
    showBack: false,
    bordered: false
  }
)

const emit = defineEmits<{
  (e: 'back'): void
}>()

function handleBack() {
  emit('back')
}
</script>

<template>
  <div class="yuxi-page-header" :class="{ 'yuxi-page-header--bordered': bordered }">
    <div class="yuxi-page-header__main">
      <button
        v-if="showBack"
        type="button"
        class="yuxi-page-header__back"
        aria-label="返回"
        @click="handleBack"
      >
        <ArrowLeft :size="18" />
      </button>
      <div class="yuxi-page-header__titles">
        <h1 class="yuxi-page-header__title">{{ title }}</h1>
        <p v-if="description" class="yuxi-page-header__description">{{ description }}</p>
      </div>
    </div>
    <div v-if="$slots.extra" class="yuxi-page-header__extra">
      <slot name="extra" />
    </div>
  </div>
</template>
