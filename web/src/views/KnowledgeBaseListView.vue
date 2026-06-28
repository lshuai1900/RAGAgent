<script setup lang="ts">
/**
 * 知识库列表页（Yuxi 风格 1:1 复刻）
 *
 * 视觉规格（参考 Yuxi DataBaseView，不复制源码）：
 * - PageHeader：sticky + 半透明白 + blur，标题"知识库" + loading 条
 * - PageShoulder：搜索框 + 新建知识库按钮
 * - 卡片网格：repeat(auto-fill, minmax(280px, 1fr))，gap:16px，padding:16px var(--page-padding)
 * - 空状态：min-height:300px，padding:72px 20px，居中，48×48 图标框，18px/600 标题，14px/#697070 描述
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Button, Spin, Alert } from 'ant-design-vue'
import { Plus, Database } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import PageHeader from '@/components/PageHeader.vue'
import PageShoulder from '@/components/PageShoulder.vue'
import KnowledgeBaseCard from '@/components/KnowledgeBaseCard.vue'
import KnowledgeBaseCreateModal from '@/components/KnowledgeBaseCreateModal.vue'

const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { list, listState, listError, total } = storeToRefs(kbStore)

const createModalOpen = ref<boolean>(false)
const searchQuery = ref<string>('')

const isLoading = computed(() => listState.value === 'loading')
const isError = computed(() => listState.value === 'error' && !isLoading.value)
const isEmpty = computed(() => listState.value === 'success' && filteredList.value.length === 0 && !searchQuery.value)
const isSearchEmpty = computed(() => listState.value === 'success' && filteredList.value.length === 0 && !!searchQuery.value)

/** 按搜索关键字过滤 */
const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list.value
  return list.value.filter(
    (kb) => kb.name.toLowerCase().includes(q) || (kb.description ?? '').toLowerCase().includes(q),
  )
})

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
    <!-- 顶部标题栏 -->
    <PageHeader
      title="知识库"
      subtitle="管理用于 RAG 问答的知识库"
      :loading="isLoading"
    />

    <!-- 肩部操作栏：搜索 + 新建 -->
    <PageShoulder
      v-model:search="searchQuery"
      search-placeholder="搜索知识库..."
    >
      <template #actions>
        <Button type="primary" @click="openCreate">
          <template #icon><Plus :size="16" /></template>
          新建知识库
        </Button>
      </template>
    </PageShoulder>

    <!-- 内容区 -->
    <div class="kb-list-view__content">
      <Alert
        v-if="isError"
        type="error"
        show-icon
        :message="listError || '加载知识库列表失败'"
        class="kb-list-view__alert"
      />

      <!-- 加载中 -->
      <div v-if="isLoading && list.length === 0" class="kb-list-view__loading">
        <Spin tip="正在加载知识库..." size="large" />
      </div>

      <!-- 空状态：暂无知识库 -->
      <div v-else-if="isEmpty" class="kb-list-view__empty">
        <div class="kb-list-view__empty-icon">
          <Database :size="24" :stroke-width="1.8" />
        </div>
        <div class="kb-list-view__empty-title">暂无知识库</div>
        <div class="kb-list-view__empty-desc">请先新建一个知识库，开始管理用于 RAG 问答的知识内容。</div>
        <div class="kb-list-view__empty-actions">
          <Button type="primary" @click="openCreate">
            <template #icon><Plus :size="16" /></template>
            新建知识库
          </Button>
        </div>
      </div>

      <!-- 搜索无结果 -->
      <div v-else-if="isSearchEmpty" class="kb-list-view__empty">
        <div class="kb-list-view__empty-icon">
          <Database :size="24" :stroke-width="1.8" />
        </div>
        <div class="kb-list-view__empty-title">未找到匹配的知识库</div>
        <div class="kb-list-view__empty-desc">没有名称或描述包含"{{ searchQuery }}"的知识库。</div>
      </div>

      <!-- 卡片网格 -->
      <div v-else-if="filteredList.length > 0" class="kb-list-view__grid">
        <KnowledgeBaseCard
          v-for="kb in filteredList"
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
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.kb-list-view__content {
  padding: 16px var(--page-padding);
  min-height: 200px;
}

.kb-list-view__alert {
  margin-bottom: 16px;
}

.kb-list-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 空状态（Yuxi ResourceEmptyState 风格） */
.kb-list-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 300px;
  padding: 72px 20px;
  text-align: center;
}

.kb-list-view__empty-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--kb-radius);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-bg);
  border: 1px solid var(--kb-border);
  color: var(--kb-primary-hover);
  margin-bottom: 8px;
}

.kb-list-view__empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--kb-text-title);
}

.kb-list-view__empty-desc {
  font-size: 14px;
  color: var(--kb-text-tertiary);
  max-width: 360px;
  line-height: 1.6;
}

.kb-list-view__empty-actions {
  margin-top: 20px;
  display: flex;
  gap: 8px;
}

/* 卡片网格：自适应 */
.kb-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kb-list-view__footer {
  padding: 0 var(--page-padding) 16px;
  font-size: 13px;
  color: var(--kb-text-quaternary);
}
</style>
