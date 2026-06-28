<script setup lang="ts">
/**
 * 仪表盘：调用 GET /health 展示后端健康状态
 * 展示：系统状态、应用名称、运行环境、PostgreSQL、Milvus、追踪编号、刷新按钮
 */
import { onMounted, onUnmounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Card, Tag, Button, Spin, Empty, Descriptions, DescriptionsItem } from 'ant-design-vue'
import { RefreshCw, ServerCog } from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import {
  healthStatusText,
  healthStatusColor,
  componentStatusText,
  componentStatusColor,
  formatTime,
} from '@/utils/format'

const appStore = useAppStore()
const { healthState, healthData, healthError } = storeToRefs(appStore)

const isLoading = computed(() => healthState.value === 'loading')
const hasError = computed(() => healthState.value === 'error' && !isLoading.value)
const hasData = computed(() => healthState.value === 'success' && healthData.value !== null)

const pg = computed(() => healthData.value?.components.postgres ?? null)
const milvus = computed(() => healthData.value?.components.milvus ?? null)

function refresh(): void {
  void appStore.fetchHealth()
}

onMounted(() => {
  refresh()
})

onUnmounted(() => {
  // store 内部会 abort 进行中的请求
})
</script>

<template>
  <div class="dashboard">
    <Card class="dashboard__card" :bordered="true" :body-style="{ padding: '20px 24px' }">
      <template #title>
        <div class="dashboard__card-title">
          <ServerCog :size="16" />
          <span>系统状态</span>
        </div>
      </template>
      <template #extra>
        <Button :icon="null" :loading="isLoading" @click="refresh">
          <template #icon><RefreshCw :size="14" /></template>
          刷新状态
        </Button>
      </template>

      <Spin :spinning="isLoading" tip="加载中…">
        <div v-if="hasData && healthData" class="dashboard__body">
          <div class="dashboard__summary">
            <span class="dashboard__summary-label">系统状态：</span>
            <Tag :color="healthStatusColor(healthData.status)">
              {{ healthStatusText(healthData.status) }}
            </Tag>
          </div>
          <Descriptions :column="1" size="small" bordered :label-style="{ width: '140px' }">
            <DescriptionsItem label="应用名称">{{ healthData.app }}</DescriptionsItem>
            <DescriptionsItem label="运行环境">{{ healthData.env }}</DescriptionsItem>
            <DescriptionsItem label="PostgreSQL 数据库">
              <div class="dashboard__component">
                <Tag :color="componentStatusColor(pg?.status ?? '')">
                  {{ componentStatusText(pg?.status ?? '') }}
                </Tag>
                <span v-if="pg?.latency_ms !== null && pg?.latency_ms !== undefined" class="dashboard__component-meta">
                  延迟 {{ pg.latency_ms }} ms
                </span>
                <span v-if="pg?.error" class="dashboard__component-error">{{ pg.error }}</span>
              </div>
            </DescriptionsItem>
            <DescriptionsItem label="Milvus 向量库">
              <div class="dashboard__component">
                <Tag :color="componentStatusColor(milvus?.status ?? '')">
                  {{ componentStatusText(milvus?.status ?? '') }}
                </Tag>
                <span
                  v-if="milvus?.latency_ms !== null && milvus?.latency_ms !== undefined"
                  class="dashboard__component-meta"
                >
                  延迟 {{ milvus.latency_ms }} ms
                </span>
                <span v-if="milvus?.error" class="dashboard__component-error">{{ milvus.error }}</span>
              </div>
            </DescriptionsItem>
            <DescriptionsItem label="追踪编号">
              <span class="dashboard__trace-id">{{ healthData.trace_id || '-' }}</span>
            </DescriptionsItem>
            <DescriptionsItem label="检查时间">{{ formatTime(healthData.timestamp) }}</DescriptionsItem>
          </Descriptions>
        </div>

        <div v-else-if="hasError" class="dashboard__error">
          <Empty :description="healthError || '后端服务连接失败，请检查 API 地址或服务状态'" />
        </div>

        <div v-else-if="!isLoading" class="dashboard__idle">
          <Empty description="点击右上角刷新状态以获取后端健康状态" />
        </div>
      </Spin>
    </Card>

    <Card class="dashboard__card" :bordered="true">
      <template #title>说明</template>
      <ul class="dashboard__tips">
        <li>当前页面展示后端 <code>GET /health</code> 的检查结果，包含 PostgreSQL 与 Milvus 的连通性。</li>
        <li>如需更换后端地址，请前往「设置」修改"后端 API 地址"。</li>
        <li>知识库管理请前往左侧菜单「知识库」，聊天问答请前往「聊天问答」。</li>
      </ul>
    </Card>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 960px;
}

.dashboard__card {
  border-radius: var(--app-radius);
}

.dashboard__card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.dashboard__summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.dashboard__summary-label {
  font-weight: 500;
}

.dashboard__component {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dashboard__component-meta {
  color: var(--app-text-tertiary);
  font-size: 13px;
}

.dashboard__component-error {
  color: #cf1322;
  font-size: 13px;
}

.dashboard__trace-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: var(--app-text-secondary);
}

.dashboard__error,
.dashboard__idle {
  padding: 16px 0;
}

.dashboard__tips {
  margin: 0;
  padding-left: 20px;
  color: var(--app-text-secondary);
  line-height: 1.9;
}

.dashboard__tips code {
  background-color: #fafafa;
  border: 1px solid var(--app-border);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--app-text);
}
</style>
