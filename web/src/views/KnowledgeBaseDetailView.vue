<script setup lang="ts">
/**
 * 知识库详情页（P1.2 基础占位）
 * - 调用 GET /api/v1/knowledge-bases/{kb_id} 展示基本信息
 * - 标签页仅占位：文件管理 / 检索测试 / 聊天问答 / 配置
 * - 不接文档 API，不做上传，不做聊天
 */
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Card, Tag, Button, Spin, Empty, Alert, Tabs, TabPane, Descriptions, DescriptionsItem } from 'ant-design-vue'
import { ArrowLeft, RefreshCw } from 'lucide-vue-next'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import {
  knowledgeBaseStatusText,
  knowledgeBaseStatusColor,
  formatTime,
} from '@/utils/format'

const route = useRoute()
const router = useRouter()
const kbStore = useKnowledgeBaseStore()
const { detail, detailState, detailError } = storeToRefs(kbStore)

const activeTab = ref<'documents' | 'retrieve' | 'chat' | 'config'>('documents')

const kbId = computed(() => String(route.params.kbId ?? ''))

const isLoading = computed(() => detailState.value === 'loading')
const isError = computed(() => detailState.value === 'error' && !isLoading.value)

function goBack(): void {
  router.push('/knowledge-bases')
}

function refresh(): void {
  if (kbId.value) {
    void kbStore.fetchDetail(kbId.value)
  }
}

onMounted(() => {
  refresh()
})

onBeforeUnmount(() => {
  kbStore.resetDetail()
})
</script>

<template>
  <div class="kb-detail">
    <!-- 顶部：返回 + 标题 -->
    <div class="kb-detail__topbar">
      <Button type="text" class="kb-detail__back" @click="goBack">
        <template #icon><ArrowLeft :size="16" /></template>
        返回知识库
      </Button>
      <Button :loading="isLoading" size="small" @click="refresh">
        <template #icon><RefreshCw :size="14" /></template>
        刷新
      </Button>
    </div>

    <!-- 加载中 -->
    <div v-if="isLoading" class="kb-detail__loading">
      <Spin tip="加载中…" size="large" />
    </div>

    <!-- 错误 -->
    <Alert
      v-else-if="isError"
      type="error"
      show-icon
      :message="detailError || '加载知识库详情失败'"
    />

    <!-- 基本信息 -->
    <Card v-else-if="detail" class="kb-detail__info" :bordered="true">
      <template #title>
        <div class="kb-detail__info-title">
          <span>{{ detail.name }}</span>
          <Tag :color="knowledgeBaseStatusColor(detail.status)">
            {{ knowledgeBaseStatusText(detail.status) }}
          </Tag>
        </div>
      </template>

      <Descriptions :column="2" size="small" bordered :label-style="{ width: '120px' }">
        <DescriptionsItem label="描述">{{ detail.description || '暂无描述' }}</DescriptionsItem>
        <DescriptionsItem label="状态">
          <Tag :color="knowledgeBaseStatusColor(detail.status)">
            {{ knowledgeBaseStatusText(detail.status) }}
          </Tag>
        </DescriptionsItem>
        <DescriptionsItem label="向量维度">{{ detail.embedding_dim }}</DescriptionsItem>
        <DescriptionsItem label="集合名称">
          <span class="kb-detail__mono">{{ detail.collection_name }}</span>
        </DescriptionsItem>
        <DescriptionsItem label="文档数量">{{ detail.document_count }}</DescriptionsItem>
        <DescriptionsItem label="创建时间">{{ formatTime(detail.created_at) }}</DescriptionsItem>
      </Descriptions>
    </Card>

    <!-- 标签页占位 -->
    <Card v-if="!isLoading && !isError && detail" class="kb-detail__tabs" :bordered="true" :body-style="{ padding: '0' }">
      <Tabs v-model:active-key="activeTab" class="kb-detail__tabs-inner">
        <TabPane key="documents" tab="文件管理">
          <div class="kb-detail__placeholder">
            <Empty description="文件管理将在 P1.3 实现" />
          </div>
        </TabPane>
        <TabPane key="retrieve" tab="检索测试">
          <div class="kb-detail__placeholder">
            <Empty description="检索测试将在 P1.4 实现" />
          </div>
        </TabPane>
        <TabPane key="chat" tab="聊天问答">
          <div class="kb-detail__placeholder">
            <Empty description="聊天问答将在 P1.4 实现" />
          </div>
        </TabPane>
        <TabPane key="config" tab="配置">
          <div class="kb-detail__placeholder">
            <Empty description="配置能力将在后续实现" />
          </div>
        </TabPane>
      </Tabs>
    </Card>
  </div>
</template>

<style scoped>
.kb-detail {
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.kb-detail__topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-detail__back {
  padding: 0 4px;
}

.kb-detail__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}

.kb-detail__info,
.kb-detail__tabs {
  border-radius: var(--app-radius);
}

.kb-detail__info-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
}

.kb-detail__mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.kb-detail__tabs-inner {
  padding: 0 24px;
}

.kb-detail__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}
</style>
