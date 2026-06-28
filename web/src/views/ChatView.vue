<script setup lang="ts">
/**
 * 全局聊天问答页（P1.4-B）
 *
 * - 路由：/chat
 * - 顶部选择知识库（加载知识库列表）
 * - 选中知识库后复用 ChatSsePanel（mode='chat', layout='horizontal'）
 * - 未选择知识库时提示"请选择知识库"
 * - 切换知识库时重置聊天 store
 * - 使用 fetch + ReadableStream 解析 SSE，不使用 EventSource
 */
import { computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { Card, Select, Spin, Empty, Alert } from 'ant-design-vue'
import { MessageSquare } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { useChatStore } from '@/stores/chat'
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
    <!-- 顶部：知识库选择区 -->
    <Card :bordered="true" size="small" class="chat-view__selector-card">
      <div class="chat-view__selector">
        <div class="chat-view__selector-label">
          <MessageSquare :size="16" class="chat-view__selector-icon" />
          <span>聊天问答</span>
        </div>
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
    </Card>

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
    <Card v-else-if="!hasSelectedKb" :bordered="true" class="chat-view__empty-card">
      <Empty
        :image="Empty.PRESENTED_IMAGE_SIMPLE"
        description="请选择知识库后再提问"
      />
    </Card>

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
</template>

<style scoped>
.chat-view {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chat-view__selector-card {
  border-radius: var(--app-radius);
}

.chat-view__selector {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-view__selector-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
}

.chat-view__selector-icon {
  color: #1677ff;
}

.chat-view__select {
  min-width: 280px;
  max-width: 400px;
}

.chat-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.chat-view__empty-card {
  border-radius: var(--app-radius);
}

.chat-view__empty-card :deep(.ant-card-body) {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}
</style>
