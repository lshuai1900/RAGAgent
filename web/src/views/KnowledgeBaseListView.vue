<script setup lang="ts">
/**
 * 知识库列表页（Yuxi 风格基座组件）
 *
 * - YuxiPageHeader：标题 + 描述 + 右侧刷新/新建按钮
 * - 内容区顶部：搜索框（Yuxi PageShoulder 风格）
 * - 状态：loading / error / empty / data
 * - 卡片网格：自适应（大屏 3+ / 中屏 2 / 小屏 1）
 * - 调用真实 GET /api/v1/knowledge-bases，失败显示中文错误
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Button, Spin, Input } from 'ant-design-vue'
import { Plus, RefreshCw, Search, Database, AlertCircle } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import YuxiPageHeader from '@/components/yuxi/YuxiPageHeader.vue'
import YuxiCard from '@/components/yuxi/YuxiCard.vue'
import YuxiEmptyState from '@/components/yuxi/YuxiEmptyState.vue'
import KnowledgeBaseCard from '@/components/KnowledgeBaseCard.vue'
import KnowledgeBaseCreateModal from '@/components/KnowledgeBaseCreateModal.vue'

const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { list, listState, listError, total } = storeToRefs(kbStore)

const createModalOpen = ref<boolean>(false)
const searchQuery = ref<string>('')

const isLoading = computed(() => listState.value === 'loading')
const isError = computed(() => listState.value === 'error' && !isLoading.value)
const isEmpty = computed(
  () => listState.value === 'success' && filteredList.value.length === 0 && !searchQuery.value
)
const isSearchEmpty = computed(
  () => listState.value === 'success' && filteredList.value.length === 0 && !!searchQuery.value
)

/** 按搜索关键字过滤 */
const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return list.value
  return list.value.filter(
    (kb) =>
      kb.name.toLowerCase().includes(q) || (kb.description ?? '').toLowerCase().includes(q)
  )
})

function refresh(): void {
  void kbStore.fetchList()
}

function openCreate(): void {
  createModalOpen.value = true
}

function enterDetail(kbId: string): void {
  void router.push(`/knowledge-bases/${kbId}`)
}

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="kb-list-view">
    <YuxiPageHeader
      title="知识库"
      description="创建和管理知识库，上传文档后构建向量索引并进行 RAG 问答"
      bordered
    >
      <template #extra>
        <Button :loading="isLoading" @click="refresh">
          <template #icon><RefreshCw :size="14" /></template>
          刷新
        </Button>
        <Button type="primary" @click="openCreate">
          <template #icon><Plus :size="14" /></template>
          新建知识库
        </Button>
      </template>
    </YuxiPageHeader>

    <!-- 搜索栏（Yuxi PageShoulder 风格） -->
    <div class="kb-list-view__shoulder">
      <div class="kb-list-view__shoulder-left">
        <Input
          v-model:value="searchQuery"
          placeholder="搜索知识库..."
          allow-clear
          class="kb-list-view__search"
        >
          <template #prefix><Search :size="14" class="kb-list-view__search-icon" /></template>
        </Input>
      </div>
      <div v-if="listState === 'success' && total > 0" class="kb-list-view__shoulder-stat">
        共 {{ total }} 个知识库
      </div>
    </div>

    <!-- 内容区 -->
    <div class="kb-list-view__content">
      <!-- 加载中（首次加载） -->
      <div v-if="isLoading && list.length === 0" class="kb-list-view__loading">
        <Spin tip="正在加载知识库..." size="large" />
      </div>

      <!-- 错误状态 -->
      <YuxiCard v-else-if="isError" flat>
        <template #default>
          <div class="kb-list-view__error">
            <div class="kb-list-view__error-icon">
              <AlertCircle :size="36" />
            </div>
            <div class="kb-list-view__error-title">加载知识库列表失败</div>
            <div class="kb-list-view__error-desc">
              {{ listError || '请检查 API 地址或服务状态' }}
            </div>
            <Button type="primary" :loading="isLoading" @click="refresh">
              <template #icon><RefreshCw :size="14" /></template>
              重新加载
            </Button>
          </div>
        </template>
      </YuxiCard>

      <!-- 空状态：暂无知识库 -->
      <YuxiEmptyState
        v-else-if="isEmpty"
        title="暂无知识库"
        description="请先新建一个知识库，开始管理用于 RAG 问答的知识内容。"
        :icon="Database"
      >
        <template #action>
          <Button type="primary" @click="openCreate">
            <template #icon><Plus :size="14" /></template>
            新建知识库
          </Button>
        </template>
      </YuxiEmptyState>

      <!-- 搜索无结果 -->
      <YuxiEmptyState
        v-else-if="isSearchEmpty"
        title="未找到匹配的知识库"
        :description="`没有名称或描述包含“${searchQuery}”的知识库。`"
        :icon="Search"
        size="compact"
      />

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

/* 搜索栏 */
.kb-list-view__shoulder {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px var(--kb-page-padding, 24px) 0;
}

.kb-list-view__shoulder-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-list-view__search {
  width: 280px;
  display: flex;
  align-items: center;
}

.kb-list-view__search :deep(.ant-input-affix-wrapper) {
  height: 32px;
  padding: 0 10px;
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
  background-color: var(--yuxi-gray-0);
}

.kb-list-view__search :deep(.ant-input-affix-wrapper:hover),
.kb-list-view__search :deep(.ant-input-affix-wrapper:focus),
.kb-list-view__search :deep(.ant-input-affix-wrapper.ant-input-affix-wrapper-focused) {
  border-color: var(--yuxi-gray-200);
  box-shadow: none;
}

.kb-list-view__search :deep(.ant-input-prefix) {
  margin-right: 8px;
  color: var(--yuxi-gray-400);
}

.kb-list-view__search :deep(.ant-input) {
  height: 100%;
  background-color: transparent;
}

.kb-list-view__search-icon {
  color: var(--yuxi-gray-400);
}

.kb-list-view__shoulder-stat {
  font-size: 13px;
  color: var(--yuxi-gray-500);
}

/* 内容区 */
.kb-list-view__content {
  padding: 16px var(--kb-page-padding, 24px);
  min-height: 200px;
}

.kb-list-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 错误状态 */
.kb-list-view__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 0 24px;
  text-align: center;
}

.kb-list-view__error-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
  margin-bottom: 6px;
}

.kb-list-view__error-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.kb-list-view__error-desc {
  font-size: 13px;
  color: var(--yuxi-gray-600);
  margin-bottom: 6px;
  text-align: center;
  max-width: 480px;
  word-break: break-all;
}

/* 卡片网格：自适应 */
.kb-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

/* 移动端：搜索栏与网格降级 */
@media (max-width: 767px) {
  .kb-list-view__shoulder {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .kb-list-view__search {
    width: 100%;
  }
  .kb-list-view__grid {
    grid-template-columns: 1fr;
  }
}
</style>
