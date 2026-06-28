<script setup lang="ts">
/**
 * 页面顶部标题栏（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi PageHeader，不复制源码）：
 * - sticky top:0，z-index:1000
 * - 背景 rgba(255,255,255,0.6) + backdrop-filter:blur(10px)
 * - padding:14px var(--page-padding)
 * - show-border 态：border-bottom:1px solid #eff2f2
 * - 标题：font-size:20px; font-weight:600; color:#0c0d0d
 * - Tab 区（可选）：与标题基线对齐，gap:2px，左侧 padding-left:12px + border-left:1px solid #e4e6e6，高 18px
 *   tab-item：高 28px，内边距 0 10px，圆角 6px，字号 15px/500，默认色 #697070
 *   hover：色 #1e1f1f，底 #f5f7f7
 *   active：色主色 #046a82，底 color-mix(主色 6%, 白)
 * - loading 条：顶部 2px 高横条，主色，宽 30%，动画 1.5s linear infinite 从左 -30% 到 100%
 */
import { computed } from 'vue'

interface TabItem {
  key: string
  label: string
}

interface Props {
  /** 页面标题 */
  title: string
  /** 副标题（可选，标题右侧小字） */
  subtitle?: string
  /** Tab 选项（可选） */
  tabs?: TabItem[]
  /** 当前激活的 Tab key（与 tabs 配合） */
  activeKey?: string
  /** 是否显示加载条 */
  loading?: boolean
  /** 是否显示底边框 */
  showBorder?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  showBorder: true,
})

interface Emits {
  (e: 'tab-change', key: string): void
}
const emit = defineEmits<Emits>()

const hasTabs = computed(() => Array.isArray(props.tabs) && props.tabs.length > 0)

function handleTabClick(key: string): void {
  if (key !== props.activeKey) {
    emit('tab-change', key)
  }
}
</script>

<template>
  <header
    class="page-header"
    :class="{ 'page-header--border': showBorder }"
  >
    <!-- 加载条 -->
    <div v-if="loading" class="page-header__loading-bar" />

    <div class="page-header__inner">
      <!-- 标题区 -->
      <div class="page-header__title-area">
        <h1 class="page-header__title">{{ title }}</h1>
        <span v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</span>
      </div>

      <!-- Tab 区 -->
      <nav v-if="hasTabs" class="page-header__tabs" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          role="tab"
          class="page-header__tab"
          :class="{ 'page-header__tab--active': activeKey === tab.key }"
          :aria-selected="activeKey === tab.key"
          @click="handleTabClick(tab.key)"
        >
          {{ tab.label }}
        </button>
      </nav>

      <!-- 右侧操作区 -->
      <div v-if="$slots.actions" class="page-header__actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.page-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  background-color: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  padding: 14px var(--page-padding);
}

.page-header--border {
  border-bottom: 1px solid var(--kb-border-light);
}

/* 加载条 */
.page-header__loading-bar {
  position: absolute;
  top: 0;
  left: 0;
  height: 2px;
  width: 30%;
  background-color: var(--kb-primary);
  animation: page-header-loading 1.5s linear infinite;
}

@keyframes page-header-loading {
  0% {
    left: -30%;
  }
  100% {
    left: 100%;
  }
}

.page-header__inner {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 28px;
}

/* 标题区 */
.page-header__title-area {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--kb-text-strong);
  line-height: 1.2;
  white-space: nowrap;
}

.page-header__subtitle {
  font-size: 13px;
  color: var(--kb-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Tab 区 */
.page-header__tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-left: 12px;
  margin-left: 4px;
  border-left: 1px solid var(--kb-border-strong);
  min-height: 18px;
}

.page-header__tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 10px;
  border: none;
  background: transparent;
  border-radius: var(--kb-radius-sm);
  font-size: 15px;
  font-weight: 500;
  color: var(--kb-text-tertiary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.page-header__tab:hover {
  color: var(--kb-text-title);
  background-color: var(--kb-bg-hover);
}

.page-header__tab--active {
  color: var(--kb-primary-hover);
  background-color: rgba(36, 131, 154, 0.06);
}

/* 操作区 */
.page-header__actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
