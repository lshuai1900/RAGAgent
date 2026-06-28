<script setup lang="ts">
/**
 * 知识库列表页（P1.8 / Yuxi 风格高保真）
 * - 顶部标题区：标题 + 副标题 + 右侧刷新 / 新建知识库
 * - 卡片网格：3 列响应式
 * - 空状态：暂无知识库，请先新建一个知识库
 * - 错误 / 加载态使用统一蓝绿色主题
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Button, Spin, Alert } from 'ant-design-vue'
import { Plus, RefreshCw, Database } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import KnowledgeBaseCard from '@/components/KnowledgeBaseCard.vue'
import KnowledgeBaseCreateModal from '@/components/KnowledgeBaseCreateModal.vue'

const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { list, listState, listError, total } = storeToRefs(kbStore)

const createModalOpen = ref<boolean>(false)

const isLoading = computed(() => listState.value === 'loading')
const isError = computed(() => listState.value === 'error' && !isLoading.value)
const isEmpty = computed(() => listState.value === 'success' && list.value.length === 0)

function refresh(): void {
  void kbStore.fetchList()
}

function openCreate(): void {
  createModalOpen.value = true
}

function enterDetail(kbId: string): void {
  router.push(`/knowledge-bases/${kbId}`)
}

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="kb-list-view">
    <!-- 顶部标题区 -->
    <div class="kb-list-view__header">
      <div class="kb-list-view__heading">
        <div class="kb-list-view__icon">
          <Database :size="20" />
        </div>
        <div class="kb-list-view__heading-text">
          <h2 class="kb-list-view__title">知识库</h2>
          <p class="kb-list-view__desc">管理用于 RAG 问答的知识库</p>
        </div>
      </div>
      <div class="kb-list-view__actions">
        <Button :loading="isLoading" @click="refresh">
          <template #icon><RefreshCw :size="14" /></template>
          刷新
        </Button>
        <Button type="primary" @click="openCreate">
          <template #icon><Plus :size="14" /></template>
          新建知识库
        </Button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="kb-list-view__content">
      <Alert
        v-if="isError"
        type="error"
        show-icon
        :message="listError || '加载知识库列表失败'"
        class="kb-list-view__alert"
      />

      <div v-if="isLoading" class="kb-list-view__loading">
        <Spin tip="加载中…" size="large" />
      </div>

      <div v-else-if="isEmpty" class="kb-list-view__empty">
        <div class="kb-list-view__empty-icon">
          <Database :size="48" />
        </div>
        <div class="kb-list-view__empty-title">暂无知识库</div>
        <div class="kb-list-view__empty-desc">请先新建一个知识库</div>
        <Button type="primary" @click="openCreate">
          <template #icon><Plus :size="14" /></template>
          新建知识库
        </Button>
      </div>

      <div v-else-if="list.length > 0" class="kb-list-view__grid">
        <KnowledgeBaseCard
          v-for="kb in list"
          :key="kb.id"
          :knowledge-base="kb"
          @enter="enterDetail"
        />
      </div>
    </div>

    <!-- 列表统计 -->
    <div v-if="listState === 'success' && total > 0" class="kb-list-view__footer">
      共 {{ total }} 个知识库
    </div>

    <!-- 新建知识库弹窗 -->
    <KnowledgeBaseCreateModal v-model:open="createModalOpen" @created="refresh" />
  </div>
</template>

<style scoped>
.kb-list-view {
  max-width: 1200px;
}

.kb-list-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.kb-list-view__heading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.kb-list-view__icon {
  width: 40px;
  height: 40px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-soft);
  color: var(--kb-primary);
  flex-shrink: 0;
}

.kb-list-view__heading-text {
  min-width: 0;
}

.kb-list-view__title {
  margin: 0 0 2px;
  font-size: 20px;
  font-weight: 600;
  color: var(--kb-text);
  line-height: 1.2;
}

.kb-list-view__desc {
  margin: 0;
  font-size: 13px;
  color: var(--kb-text-tertiary);
}

.kb-list-view__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.kb-list-view__content {
  min-height: 200px;
}

.kb-list-view__alert {
  margin-bottom: 16px;
}

.kb-list-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.kb-list-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 70px 0;
}

.kb-list-view__empty-icon {
  width: 72px;
  height: 72px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-soft);
  color: var(--kb-primary);
  margin-bottom: 6px;
}

.kb-list-view__empty-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--kb-text);
}

.kb-list-view__empty-desc {
  font-size: 13px;
  color: var(--kb-text-tertiary);
  margin-bottom: 6px;
}

.kb-list-view__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

@media (max-width: 1100px) {
  .kb-list-view__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 720px) {
  .kb-list-view__grid {
    grid-template-columns: 1fr;
  }
}

.kb-list-view__footer {
  margin-top: 18px;
  font-size: 13px;
  color: var(--kb-text-tertiary);
}
</style>
