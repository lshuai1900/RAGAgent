<script setup lang="ts">
/**
 * 知识库详情页（Yuxi 风格沉浸式布局）
 *
 * 仅作为父布局：沉浸式 Header + 横向 Tabs + RouterView 子路由出口。
 * - Header：返回 / 名称 / 描述 / 状态徽标 / 元信息 / 复制ID / 编辑 / 刷新
 * - Tabs：文件管理 / 检索测试 / 聊天问答（仅 3 个真实 Tab，无 planned tabs）
 * - 子路由渲染各 Tab 内容（KbFilesTab / KbRetrievalTab / KbChatTab）
 *
 * 编辑/删除知识库通过 KnowledgeBaseEditModal 完成。
 */
import { computed, onMounted, onBeforeUnmount, watch, ref } from 'vue'
import { useRoute, useRouter, RouterView } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Spin } from 'ant-design-vue'
import { AlertCircle, RefreshCw } from 'lucide-vue-next'
import { Button } from 'ant-design-vue'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import KnowledgeBaseDetailHeader from '@/components/KnowledgeBaseDetailHeader.vue'
import KnowledgeBaseTabs from '@/components/KnowledgeBaseTabs.vue'
import KnowledgeBaseEditModal from '@/components/KnowledgeBaseEditModal.vue'
import YuxiCard from '@/components/yuxi/YuxiCard.vue'

const route = useRoute()
const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { detail, detailState, detailError } = storeToRefs(kbStore)

const kbId = computed(() => String(route.params.kbId ?? ''))

const editModalOpen = ref<boolean>(false)

const isKbLoading = computed(() => detailState.value === 'loading')
const isKbError = computed(() => detailState.value === 'error' && !isKbLoading.value)

function goBack(): void {
  void router.push('/knowledge-bases')
}

function refreshKb(): void {
  if (kbId.value) void kbStore.fetchDetail(kbId.value)
}

function openEdit(): void {
  editModalOpen.value = true
}

function handleUpdated(): void {
  if (kbId.value) void kbStore.fetchDetail(kbId.value)
}

function handleDeleted(): void {
  void router.push('/knowledge-bases')
}

/** 切换知识库时重新加载详情 */
watch(
  kbId,
  (id) => {
    if (!id) return
    void kbStore.fetchDetail(id)
  },
  { immediate: false }
)

onMounted(() => {
  if (kbId.value) void kbStore.fetchDetail(kbId.value)
})

onBeforeUnmount(() => {
  kbStore.resetDetail()
})
</script>

<template>
  <div class="kb-detail">
    <!-- 错误状态：整页错误 -->
    <div v-if="isKbError" class="kb-detail__error-wrap">
      <YuxiCard flat>
        <template #default>
          <div class="kb-detail__error">
            <div class="kb-detail__error-icon">
              <AlertCircle :size="36" />
            </div>
            <div class="kb-detail__error-title">加载知识库详情失败</div>
            <div class="kb-detail__error-desc">
              {{ detailError || '知识库不存在或已被删除' }}
            </div>
            <div class="kb-detail__error-actions">
              <Button type="primary" :loading="isKbLoading" @click="refreshKb">
                <template #icon><RefreshCw :size="14" /></template>
                重新加载
              </Button>
              <Button @click="goBack">返回知识库列表</Button>
            </div>
          </div>
        </template>
      </YuxiCard>
    </div>

    <template v-else>
      <!-- 沉浸式 Header -->
      <KnowledgeBaseDetailHeader
        :knowledge-base="detail"
        :loading="isKbLoading"
        @back="goBack"
        @refresh="refreshKb"
        @edit="openEdit"
      />

      <!-- 横向 Tabs -->
      <KnowledgeBaseTabs />

      <!-- 首次加载遮罩 -->
      <div v-if="isKbLoading && !detail" class="kb-detail__loading">
        <Spin tip="加载中..." size="large" />
      </div>

      <!-- 子路由出口：渲染当前 Tab 内容 -->
      <div v-else class="kb-detail__body">
        <RouterView />
      </div>
    </template>

    <!-- 编辑知识库弹窗（含删除） -->
    <KnowledgeBaseEditModal
      v-model:open="editModalOpen"
      :knowledge-base="detail"
      @updated="handleUpdated"
      @deleted="handleDeleted"
    />
  </div>
</template>

<style scoped>
.kb-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: var(--yuxi-gray-50);
}

/* 错误整页 */
.kb-detail__error-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px var(--kb-page-padding, 24px);
}

.kb-detail__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 0 24px;
  text-align: center;
}

.kb-detail__error-icon {
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

.kb-detail__error-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.kb-detail__error-desc {
  font-size: 13px;
  color: var(--yuxi-gray-600);
  margin-bottom: 6px;
  text-align: center;
  max-width: 480px;
  word-break: break-all;
}

.kb-detail__error-actions {
  display: flex;
  gap: 8px;
}

/* 加载中 */
.kb-detail__loading {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 子路由内容区 */
.kb-detail__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
</style>
