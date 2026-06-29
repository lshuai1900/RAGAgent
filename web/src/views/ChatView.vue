<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 8：Yuxi 风格顶层 /chat 页面，含知识库选择器 + RagChatPanel。
-->
<script setup lang="ts">
/**
 * 顶层聊天问答页（Step 8 / Yuxi 风格）
 *
 * - 加载真实知识库列表（GET /api/v1/knowledge-bases）
 * - 无知识库时显示 YuxiEmptyState + 跳转按钮
 * - 有知识库时默认选择第一个，用户可切换
 * - 切换知识库时 RagChatPanel 内部自动清空消息
 * - 不显示 Agent / Tool / 会话历史入口
 */
import { computed, h, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Select, Spin, Button } from 'ant-design-vue'
import { Database, RefreshCw, MessageSquare } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import RagChatPanel from '@/components/chat/RagChatPanel.vue'
import YuxiEmptyState from '@/components/yuxi/YuxiEmptyState.vue'

const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { list: kbList, listState: kbListState, listError: kbListError } = storeToRefs(kbStore)

/** 当前选中的知识库 ID */
const selectedKbId = ref<string>('')

const isKbLoading = computed(() => kbListState.value === 'loading')
const isKbError = computed(() => kbListState.value === 'error')
const hasKb = computed(() => kbList.value.length > 0)

/** Select 选项 */
const kbOptions = computed(() =>
  kbList.value.map((kb) => ({
    value: kb.id,
    label: kb.name,
  })),
)

/** 选中的知识库名称 */
const selectedKbName = computed(() => {
  const kb = kbList.value.find((k) => k.id === selectedKbId.value)
  return kb?.name ?? ''
})

/** 列表加载成功后默认选中第一个 */
watch(
  () => kbListState.value,
  (state) => {
    if (state === 'success' && !selectedKbId.value && kbList.value.length > 0) {
      selectedKbId.value = kbList.value[0].id
    }
  },
)

/** 切换知识库 */
function handleKbChange(value: unknown): void {
  let kbId = ''
  if (typeof value === 'string') {
    kbId = value
  } else if (typeof value === 'number') {
    kbId = String(value)
  } else if (value && typeof value === 'object' && 'value' in value) {
    kbId = String((value as { value: unknown }).value ?? '')
  }
  selectedKbId.value = kbId
}

function handleRefresh(): void {
  void kbStore.fetchList()
}

function goCreateKb(): void {
  router.push('/knowledge-bases')
}

onMounted(() => {
  void kbStore.fetchList()
})
</script>

<template>
  <div class="chat-view">
    <!-- 顶部标题 + 知识库选择器 -->
    <header class="chat-view__header">
      <div class="chat-view__head-left">
        <div class="chat-view__title-row">
          <MessageSquare :size="18" class="chat-view__title-icon" />
          <h1 class="chat-view__title">聊天问答</h1>
        </div>
        <p class="chat-view__subtitle">选择知识库后进行 RAG 问答，回答将展示引用来源</p>
      </div>

      <!-- 知识库选择器 -->
      <div class="chat-view__selector" v-if="hasKb || isKbLoading">
        <span class="chat-view__selector-label">当前知识库</span>
        <Select
          :value="selectedKbId || undefined"
          :options="kbOptions"
          placeholder="请选择知识库"
          :loading="isKbLoading"
          :disabled="isKbLoading"
          class="chat-view__select"
          @change="handleKbChange"
        />
        <Button :icon="h(RefreshCw, { size: 14 })" @click="handleRefresh" :loading="isKbLoading" />
      </div>
    </header>

    <!-- 内容区 -->
    <div class="chat-view__content">
      <!-- 加载中 -->
      <div v-if="isKbLoading && kbList.length === 0" class="chat-view__loading">
        <Spin tip="加载知识库列表…" size="large" />
      </div>

      <!-- 加载失败 -->
      <div v-else-if="isKbError" class="chat-view__error">
        <YuxiEmptyState
          :icon="Database"
          title="加载知识库列表失败"
          :description="kbListError || '请稍后重试'"
        >
          <template #action>
            <Button type="primary" @click="handleRefresh">
              <template #icon><RefreshCw :size="14" /></template>
              重新加载
            </Button>
          </template>
        </YuxiEmptyState>
      </div>

      <!-- 无知识库 -->
      <div v-else-if="!hasKb" class="chat-view__no-kb">
        <YuxiEmptyState
          :icon="Database"
          title="暂无知识库"
          description="请先创建知识库并上传文档，再开始问答"
        >
          <template #action>
            <Button type="primary" @click="goCreateKb">
              去创建知识库
            </Button>
          </template>
        </YuxiEmptyState>
      </div>

      <!-- 已选择知识库：展示聊天面板 -->
      <RagChatPanel
        v-else-if="selectedKbId"
        :key="selectedKbId"
        :kb-id="selectedKbId"
        :title="'当前对话'"
        :description="`基于知识库「${selectedKbName}」进行 RAG 问答`"
      />
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* ===== 顶部 ===== */
.chat-view__header {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px var(--page-padding, 24px);
  border-bottom: 1px solid var(--yuxi-gray-150);
  background: var(--yuxi-gray-0);
  flex-wrap: wrap;
}

.chat-view__head-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-view__title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-view__title-icon {
  color: var(--yuxi-main-color);
}

.chat-view__title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.chat-view__subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--yuxi-gray-600);
}

.chat-view__selector {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.chat-view__selector-label {
  font-size: 13px;
  color: var(--yuxi-gray-500);
  white-space: nowrap;
}

.chat-view__select {
  min-width: 240px;
  max-width: 360px;
}

/* ===== 内容区 ===== */
.chat-view__content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 var(--page-padding, 24px) 16px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
}

.chat-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.chat-view__error,
.chat-view__no-kb {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

/* ===== 小屏 ===== */
@media (max-width: 767px) {
  .chat-view__header {
    flex-direction: column;
    align-items: stretch;
  }

  .chat-view__selector {
    flex-wrap: wrap;
  }

  .chat-view__select {
    min-width: 0;
    flex: 1;
  }
}
</style>
