<script setup lang="ts">
/**
 * 文件类型图标（P1.6 知识库工作台）
 * - 根据文件类型展示带浅色底的扩展名徽标（TXT / MD / PDF）
 * - 仅做视觉展示，无交互
 */
import { computed } from 'vue'

interface Props {
  /** 文件类型字符串（如 'txt' / 'md' / 'pdf'） */
  fileType: string
  /** 可选尺寸：默认 36 */
  size?: number
}
const props = withDefaults(defineProps<Props>(), {
  size: 36,
})

/** 归一化文件类型 → 徽标 key */
const kind = computed<'txt' | 'md' | 'pdf' | 'file'>(() => {
  const ft = (props.fileType || '').toLowerCase()
  if (ft === 'txt') return 'txt'
  if (ft === 'md' || ft === 'markdown') return 'md'
  if (ft === 'pdf') return 'pdf'
  return 'file'
})

const label = computed(() => {
  switch (kind.value) {
    case 'txt':
      return 'TXT'
    case 'md':
      return 'MD'
    case 'pdf':
      return 'PDF'
    default:
      return 'FILE'
  }
})
</script>

<template>
  <span
    class="file-type-icon"
    :class="`file-type-icon--${kind}`"
    :style="{ width: `${size}px`, height: `${size * 0.78}px` }"
    :title="label"
  >
    {{ label }}
  </span>
</template>

<style scoped>
.file-type-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  flex-shrink: 0;
  user-select: none;
  border: 1px solid transparent;
}

.file-type-icon--txt {
  color: #475569;
  background-color: #f1f5f9;
  border-color: #e2e8f0;
}

.file-type-icon--md {
  color: #1d4ed8;
  background-color: #eff6ff;
  border-color: #dbeafe;
}

.file-type-icon--pdf {
  color: #b91c1c;
  background-color: #fef2f2;
  border-color: #fee2e2;
}

.file-type-icon--file {
  color: #6b7280;
  background-color: #f3f4f6;
  border-color: #e5e7eb;
}
</style>
