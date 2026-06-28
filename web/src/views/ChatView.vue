<script setup lang="ts">
/**
 * 全局聊天问答页（Yuxi 风格 1:1 复刻）
 *
 * - PageHeader：sticky + blur，标题"聊天问答" + 副标题 + 右侧知识库选择器
 * - 选中知识库后复用 ChatSsePanel（mode='chat', layout='horizontal'）
 * - 未选择知识库时提示"请选择知识库后再提问"
 * - 切换知识库时重置聊天 store
 * - 使用 fetch + ReadableStream 解析 SSE，不使用 EventSource
 */
import { computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Select, Spin, Alert } from 'ant-design-vue'
import { MessageSquare } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { useChatStore } from '@/stores/chat'
import PageHeader from '@/components/PageHeader.vue'
import ChatSsePanel from '@/components/ChatSsePanel.vue'

const kbStore = useKnowledgeBaseStore()
const chatStore = useChatStore()
const { list: kbList, listState: kbListState, listError: kbListError } = storeToRefs(kbStore)

/** 当前选中的知识库 ID（从 chat store 读取，由 handleKbChange 设置） */
const selectedKbId = computed(() => chatStore.currentKbId)

/** 当前选中的知识库名称 */
const selectedKbName = computed(() => {
  const kb = kbList.value.find((k) => k.id === selectedKbId.value)
  return kb?.name ?? ''
})

const isKbLoading = computed(() => kbListState.value === 'loading')
const isKbError = computed(() => kbListState.value === 'error')
const hasSelectedKb = computed(() => !!selectedKbId.value)

/** Select 选项 */
const kbOptions = computed(() =>
  kbList.value.map((kb) => ({
    value: kb.id,
    label: kb.name,
  })),
)

/** 切换知识库 */
function handleKbChange(value: unknown): void {
  // SelectValue 可能是 string | number | LabeledValue，统一提取为 string
  let kbId = ''
  if (typeof value === 'string') {
    kbId = value
  } else if (typeof value === 'number') {
    kbId = String(value)
  } else if (value && typeof value === 'object' && 'value' in value) {
    kbId = String((value as { value: unknown }).value ?? '')
  }
  // 切换知识库时重置聊天会话
  if (kbId !== chatStore.currentKbId) {
    chatStore.reset()
  }
  // 直接设置 currentKbId 供 ChatSsePanel 使用
  chatStore.currentKbId = kbId
}

onMounted(() => {
  void kbStore.fetchList()
})

onBeforeUnmount(() => {
  // 离开页面时取消进行中的 SSE 请求并重置
  chatStore.reset()
})

// 监听列表加载完成后，如果之前选中的 kb 已不在列表中，则重置
watch(
  () => kbListState.value,
  (state) => {
    if (state === 'success' && selectedKbId.value) {
      const exists = kbList.value.some((kb) => kb.id === selectedKbId.value)
      if (!exists) {
        chatStore.reset()
      }
    }
  },
)
</script>

<template>
  <div class="chat-view">
    <!-- 顶部标题栏：标题 + 副标题 + 右侧知识库选择器 -->
    <PageHeader
      title="聊天问答"
      subtitle="选择知识库后进行流式问答"
    >
      <template #actions>
        <div class="chat-view__selector-wrap">
          <span class="chat-view__selector-label">知识库</span>
          <Select
            :value="selectedKbId || undefined"
            :options="kbOptions"
            placeholder="请选择知识库"
            :loading="isKbLoading"
            :disabled="isKbLoading"
            class="chat-view__select"
            @change="handleKbChange"
          />
        </div>
      </template>
    </PageHeader>

    <!-- 内容区 -->
    <div class="chat-view__content">
      <!-- 知识库列表加载中 -->
      <div v-if="isKbLoading && kbList.length === 0" class="chat-view__loading">
        <Spin tip="加载知识库列表…" size="large" />
      </div>

      <!-- 知识库列表加载失败 -->
      <Alert
        v-else-if="isKbError"
        type="error"
        show-icon
        :message="kbListError || '加载知识库列表失败'"
      />

      <!-- 未选择知识库 -->
      <div v-else-if="!hasSelectedKb" class="chat-view__empty">
        <div class="chat-view__empty-icon">
          <MessageSquare :size="40" />
        </div>
        <div class="chat-view__empty-title">请选择知识库后再提问</div>
        <div class="chat-view__empty-desc">在右上角选择一个知识库后即可开始流式问答</div>
      </div>

      <!-- 已选择知识库：展示聊天面板 -->
      <ChatSsePanel
        v-else
        :key="selectedKbId"
        :kb-id="selectedKbId"
        :kb-name="selectedKbName"
        mode="chat"
        layout="horizontal"
      />
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.chat-view__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px var(--page-padding);
  max-width: 1200px;
}

/* 知识库选择器（嵌入 PageHeader 操作区） */
.chat-view__selector-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.chat-view__selector-label {
  font-size: 13px;
  color: var(--kb-text-tertiary);
  white-space: nowrap;
}

.chat-view__select {
  min-width: 240px;
  max-width: 360px;
}

.chat-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
}

.chat-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 70px 0;
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
}

.chat-view__empty-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-soft);
  color: var(--kb-primary);
  margin-bottom: 6px;
}

.chat-view__empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--kb-text);
}

.chat-view__empty-desc {
  font-size: 13px;
  color: var(--kb-text-tertiary);
}
</style>
