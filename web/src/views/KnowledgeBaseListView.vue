<script setup lang="ts">
/**
 * 知识库列表页
 * - 卡片网格展示
 * - 新建知识库弹窗
 * - 加载中 / 空状态 / 错误提示
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Button, Spin, Empty, Alert } from 'ant-design-vue'
import { Plus, RefreshCw, Library } from 'lucide-vue-next'
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
        <h2 class="kb-list-view__title">知识库</h2>
        <p class="kb-list-view__desc">管理用于 RAG 问答的知识库</p>
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
        <Empty description="暂无知识库，请先新建一个知识库">
          <Button type="primary" @click="openCreate">
            <template #icon><Plus :size="14" /></template>
            新建知识库
          </Button>
        </Empty>
      </div>

      <div v-else-if="list.length > 0" class="kb-list-view__grid">
        <KnowledgeBaseCard
          v-for="kb in list"
          :key="kb.id"
          :knowledge-base="kb"
          @enter="enterDetail"
        />
      </div>

      <!-- 列表为空且非空态（兜底） -->
      <div v-else class="kb-list-view__empty">
        <Empty>
          <template #image>
            <Library :size="48" />
          </template>
          暂无数据
        </Empty>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.kb-list-view__heading {
  min-width: 0;
}

.kb-list-view__title {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 600;
  color: var(--app-text);
}

.kb-list-view__desc {
  margin: 0;
  font-size: 13px;
  color: var(--app-text-tertiary);
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
  align-items: center;
  justify-content: center;
  padding: 80px 0;
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
  margin-top: 16px;
  font-size: 13px;
  color: var(--app-text-tertiary);
}
</style>
