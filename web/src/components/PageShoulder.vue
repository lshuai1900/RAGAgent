<script setup lang="ts">
/**
 * 页面肩部操作栏（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi PageShoulder，不复制源码）：
 * - padding:16px var(--page-padding) 0
 * - 左右两端对齐，gap:16px
 * - 搜索框：宽 280px，高 32px，内边距 0 10px，边框 1px solid #eef0f0，圆角 8px，白底
 *   hover/focus 边框变 #e4e6e6，无 box-shadow
 *   前缀搜索图标 14px 色 #bdbfbf
 * - filters slot：筛选器
 * - actions slot：操作按钮（如新建）
 */
import { Search } from 'lucide-vue-next'

interface Props {
  /** 搜索关键字（v-model:search） */
  search?: string
  /** 搜索框 placeholder */
  searchPlaceholder?: string
  /** 是否显示搜索框 */
  showSearch?: boolean
}

withDefaults(defineProps<Props>(), {
  search: '',
  searchPlaceholder: '搜索...',
  showSearch: true,
})

interface Emits {
  (e: 'update:search', value: string): void
}
const emit = defineEmits<Emits>()

function handleInput(e: Event): void {
  const target = e.target as HTMLInputElement
  emit('update:search', target.value)
}
</script>

<template>
  <div class="page-shoulder">
    <!-- 左侧：搜索 + 筛选 -->
    <div class="page-shoulder__left">
      <div v-if="showSearch" class="page-shoulder__search">
        <Search :size="14" class="page-shoulder__search-icon" />
        <input
          type="text"
          class="page-shoulder__search-input"
          :value="search"
          :placeholder="searchPlaceholder"
          @input="handleInput"
        />
      </div>
      <slot name="filters" />
    </div>

    <!-- 右侧：操作区 -->
    <div v-if="$slots.actions" class="page-shoulder__right">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-shoulder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px var(--page-padding) 0;
  flex-wrap: wrap;
}

.page-shoulder__left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-shoulder__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 搜索框 */
.page-shoulder__search {
  position: relative;
  display: inline-flex;
  align-items: center;
  width: 280px;
  max-width: 100%;
}

.page-shoulder__search-icon {
  position: absolute;
  left: 10px;
  color: var(--kb-text-disabled);
  pointer-events: none;
  flex-shrink: 0;
}

.page-shoulder__search-input {
  width: 100%;
  height: 32px;
  padding: 0 10px 0 30px;
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  background-color: #ffffff;
  font-size: 14px;
  color: var(--kb-text);
  outline: none;
  transition: border-color 0.15s ease;
}

.page-shoulder__search-input::placeholder {
  color: var(--kb-text-disabled);
}

.page-shoulder__search-input:hover {
  border-color: var(--kb-border-strong);
}

.page-shoulder__search-input:focus {
  border-color: var(--kb-primary);
}
</style>
