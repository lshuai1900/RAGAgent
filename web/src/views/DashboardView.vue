<script setup lang="ts">
/**
 * 仪表盘（P1.8 / Yuxi 风格）
 * - 调用 GET /health 展示后端健康状态
 * - 顶部标题区 + 状态概览卡片 + 组件状态列表
 * - 不再像后台管理系统的大卡片堆叠
 * - 使用统一蓝绿色主题
 */
import { onMounted, onUnmounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { Card, Tag, Button, Spin, Empty, Descriptions, DescriptionsItem } from 'ant-design-vue'
import { RefreshCw, ServerCog, Database, Boxes, Activity } from 'lucide-vue-next'
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
    <!-- 顶部标题区 -->
    <div class="dashboard__header">
      <div class="dashboard__heading">
        <div class="dashboard__icon">
          <Activity :size="20" />
        </div>
        <div class="dashboard__heading-text">
          <h2 class="dashboard__title">系统状态</h2>
          <p class="dashboard__desc">查看后端服务与依赖组件状态</p>
        </div>
      </div>
      <Button :loading="isLoading" @click="refresh">
        <template #icon><RefreshCw :size="14" /></template>
        刷新状态
      </Button>
    </div>

    <Spin :spinning="isLoading" tip="加载中…">
      <!-- 状态概览卡片 -->
      <Card v-if="hasData && healthData" class="dashboard__card" :bordered="true">
        <div class="dashboard__summary">
          <div class="dashboard__summary-label">整体状态</div>
          <Tag :color="healthStatusColor(healthData.status)" class="dashboard__summary-tag">
            {{ healthStatusText(healthData.status) }}
          </Tag>
          <span class="dashboard__summary-app">{{ healthData.app }}</span>
          <span class="dashboard__summary-env">{{ healthData.env }}</span>
        </div>

        <Descriptions :column="1" size="small" bordered :label-style="{ width: '140px' }" class="dashboard__desc">
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
      </Card>

      <!-- 错误状态 -->
      <Card v-else-if="hasError" class="dashboard__card dashboard__card--error" :bordered="true">
        <div class="dashboard__error">
          <div class="dashboard__error-icon">
            <ServerCog :size="36" />
          </div>
          <div class="dashboard__error-title">后端服务连接失败</div>
          <div class="dashboard__error-desc">{{ healthError || '请检查 API 地址或服务状态' }}</div>
          <Button type="primary" @click="refresh">
            <template #icon><RefreshCw :size="14" /></template>
            重新加载
          </Button>
        </div>
      </Card>

      <!-- 空态 -->
      <Card v-else-if="!isLoading" class="dashboard__card" :bordered="true">
        <div class="dashboard__idle">
          <Empty description="点击右上角刷新状态以获取后端健康状态" />
        </div>
      </Card>
    </Spin>

    <!-- 组件状态卡片 -->
    <div v-if="hasData && healthData" class="dashboard__components">
      <div class="dashboard__component-card">
        <div class="dashboard__component-card-icon">
          <Database :size="18" />
        </div>
        <div class="dashboard__component-card-body">
          <div class="dashboard__component-card-title">PostgreSQL 数据库</div>
          <div class="dashboard__component-card-status">
            <Tag :color="componentStatusColor(pg?.status ?? '')">
              {{ componentStatusText(pg?.status ?? '') }}
            </Tag>
            <span v-if="pg?.latency_ms !== null && pg?.latency_ms !== undefined" class="dashboard__component-card-meta">
              延迟 {{ pg.latency_ms }} ms
            </span>
          </div>
        </div>
      </div>

      <div class="dashboard__component-card">
        <div class="dashboard__component-card-icon">
          <Boxes :size="18" />
        </div>
        <div class="dashboard__component-card-body">
          <div class="dashboard__component-card-title">Milvus 向量库</div>
          <div class="dashboard__component-card-status">
            <Tag :color="componentStatusColor(milvus?.status ?? '')">
              {{ componentStatusText(milvus?.status ?? '') }}
            </Tag>
            <span v-if="milvus?.latency_ms !== null && milvus?.latency_ms !== undefined" class="dashboard__component-card-meta">
              延迟 {{ milvus.latency_ms }} ms
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 说明卡片 -->
    <Card class="dashboard__card dashboard__tips-card" :bordered="true">
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

.dashboard__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 4px;
}

.dashboard__heading {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.dashboard__icon {
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

.dashboard__heading-text {
  min-width: 0;
}

.dashboard__title {
  margin: 0 0 2px;
  font-size: 20px;
  font-weight: 600;
  color: var(--kb-text);
  line-height: 1.2;
}

.dashboard__desc {
  margin: 0;
  font-size: 13px;
  color: var(--kb-text-tertiary);
}

.dashboard__card {
  border-radius: var(--kb-radius);
  border-color: var(--kb-border);
}

.dashboard__summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.dashboard__summary-label {
  font-weight: 500;
  color: var(--kb-text);
}

.dashboard__summary-tag {
  margin: 0;
}

.dashboard__summary-app {
  font-size: 13px;
  color: var(--kb-text-secondary);
}

.dashboard__summary-env {
  font-size: 12px;
  color: var(--kb-text-tertiary);
  padding: 2px 8px;
  background-color: var(--kb-bg);
  border: 1px solid var(--kb-border);
  border-radius: 4px;
}

.dashboard__component {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dashboard__component-meta {
  color: var(--kb-text-tertiary);
  font-size: 13px;
}

.dashboard__component-error {
  color: var(--kb-error);
  font-size: 13px;
}

.dashboard__trace-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: var(--kb-text-secondary);
}

.dashboard__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 30px 0 20px;
}

.dashboard__error-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-error-bg);
  color: var(--kb-error);
  margin-bottom: 6px;
}

.dashboard__error-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--kb-text);
}

.dashboard__error-desc {
  font-size: 13px;
  color: var(--kb-text-tertiary);
  margin-bottom: 6px;
  text-align: center;
  max-width: 480px;
}

.dashboard__idle {
  padding: 30px 0;
}

.dashboard__components {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.dashboard__component-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background-color: var(--kb-surface);
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
}

.dashboard__component-card-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--kb-primary-soft);
  color: var(--kb-primary);
  flex-shrink: 0;
}

.dashboard__component-card-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dashboard__component-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--kb-text);
}

.dashboard__component-card-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dashboard__component-card-meta {
  font-size: 12px;
  color: var(--kb-text-tertiary);
}

.dashboard__tips-card {
  border-color: var(--kb-border);
}

.dashboard__tips {
  margin: 0;
  padding-left: 20px;
  color: var(--kb-text-secondary);
  line-height: 1.9;
}

.dashboard__tips code {
  background-color: var(--kb-bg);
  border: 1px solid var(--kb-border);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--kb-text);
}
</style>
