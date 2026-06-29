<script setup lang="ts">
/**
 * 仪表盘（Yuxi 风格基座组件）
 *
 * - YuxiPageHeader：标题 + 描述 + 右侧"重新检查"按钮
 * - 第一行：健康总览卡片（总体状态 / PostgreSQL / Milvus / 检查时间 / trace_id）
 * - 第二行：快捷入口卡片（知识库 / 聊天问答 / 设置）
 * - 调用真实 GET /health，失败显示中文错误，不使用 mock 数据
 *
 * 不展示 Agent / Tool / Call stats / MCP / Skills / Graph / Evaluation 等暂缓项。
 */
import { onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { Button, Spin } from 'ant-design-vue'
import {
  RefreshCw,
  ServerCog,
  Database,
  Boxes,
  Library,
  MessageSquare,
  Settings,
  AlertTriangle,
} from 'lucide-vue-next'
import { useAppStore } from '@/stores/app'
import YuxiPageHeader from '@/components/yuxi/YuxiPageHeader.vue'
import YuxiCard from '@/components/yuxi/YuxiCard.vue'
import YuxiStatusBadge, { type YuxiStatusKind } from '@/components/yuxi/YuxiStatusBadge.vue'
import { formatTime } from '@/utils/format'
import type { ComponentStatus } from '@/types/api'

const appStore = useAppStore()
const router = useRouter()
const { healthState, healthData, healthError } = storeToRefs(appStore)

const isLoading = computed(() => healthState.value === 'loading')
const hasError = computed(() => healthState.value === 'error' && !isLoading.value)
const hasData = computed(() => healthData.value !== null && healthState.value === 'success')

const pg = computed<ComponentStatus | null>(
  () => healthData.value?.components.postgres ?? null
)
const milvus = computed<ComponentStatus | null>(
  () => healthData.value?.components.milvus ?? null
)

/** 整体状态 → YuxiStatusBadge kind */
function overallKind(status: string | undefined, loading: boolean): YuxiStatusKind {
  if (loading) return 'processing'
  switch (status) {
    case 'ok':
      return 'success'
    case 'degraded':
      return 'warning'
    case 'error':
      return 'error'
    default:
      return 'default'
  }
}

/** 组件状态 → YuxiStatusBadge kind */
function componentKind(status: string | undefined, loading: boolean): YuxiStatusKind {
  if (loading) return 'processing'
  switch (status) {
    case 'ok':
      return 'success'
    case 'error':
      return 'error'
    default:
      return 'default'
  }
}

/** 整体状态文案 */
function overallLabel(kind: YuxiStatusKind): string {
  switch (kind) {
    case 'success':
      return '正常'
    case 'warning':
      return '部分异常'
    case 'error':
      return '异常'
    case 'processing':
      return '检查中'
    default:
      return '未知'
  }
}

/** 组件状态文案 */
function componentLabel(kind: YuxiStatusKind): string {
  switch (kind) {
    case 'success':
      return '正常'
    case 'error':
      return '异常'
    case 'processing':
      return '检查中'
    default:
      return '未知'
  }
}

const overallKindValue = computed<YuxiStatusKind>(() =>
  overallKind(healthData.value?.status, isLoading.value)
)

function refresh(): void {
  // appStore.fetchHealth 内部已用 AbortController 取消上一个请求，避免并发
  void appStore.fetchHealth()
}

function go(path: string): void {
  void router.push(path)
}

onMounted(() => {
  refresh()
})
</script>

<template>
  <div class="dashboard">
    <YuxiPageHeader
      title="仪表盘"
      description="查看 RAGAgent 服务状态、知识库工作台入口与运行健康信息"
      bordered
    >
      <template #extra>
        <Button :loading="isLoading" @click="refresh">
          <template #icon><RefreshCw :size="14" /></template>
          重新检查
        </Button>
      </template>
    </YuxiPageHeader>

    <div class="dashboard__content">
      <Spin :spinning="isLoading && !hasData && !hasError" tip="正在检查后端状态…">
        <!-- ===== 第一行：健康总览 ===== -->
        <section v-if="hasData && healthData" class="dashboard__section">
          <h2 class="dashboard__section-title">服务状态</h2>
          <div class="dashboard__grid dashboard__grid--health">
            <!-- 总体状态 -->
            <YuxiCard flat>
              <template #default>
                <div class="health-cell">
                  <div class="health-cell__icon">
                    <Boxes :size="20" />
                  </div>
                  <div class="health-cell__body">
                    <div class="health-cell__label">总体状态</div>
                    <YuxiStatusBadge :kind="overallKindValue" :label="overallLabel(overallKindValue)" />
                  </div>
                </div>
              </template>
            </YuxiCard>

            <!-- PostgreSQL -->
            <YuxiCard flat>
              <template #default>
                <div class="health-cell">
                  <div class="health-cell__icon">
                    <Database :size="20" />
                  </div>
                  <div class="health-cell__body">
                    <div class="health-cell__label">PostgreSQL</div>
                    <YuxiStatusBadge
                      :kind="componentKind(pg?.status, isLoading)"
                      :label="componentLabel(componentKind(pg?.status, isLoading))"
                    />
                    <div v-if="pg?.latency_ms !== null && pg?.latency_ms !== undefined" class="health-cell__meta">
                      延迟 {{ pg.latency_ms }} ms
                    </div>
                    <div v-if="pg?.error" class="health-cell__error">{{ pg.error }}</div>
                  </div>
                </div>
              </template>
            </YuxiCard>

            <!-- Milvus -->
            <YuxiCard flat>
              <template #default>
                <div class="health-cell">
                  <div class="health-cell__icon">
                    <Boxes :size="20" />
                  </div>
                  <div class="health-cell__body">
                    <div class="health-cell__label">Milvus 向量库</div>
                    <YuxiStatusBadge
                      :kind="componentKind(milvus?.status, isLoading)"
                      :label="componentLabel(componentKind(milvus?.status, isLoading))"
                    />
                    <div
                      v-if="milvus?.latency_ms !== null && milvus?.latency_ms !== undefined"
                      class="health-cell__meta"
                    >
                      延迟 {{ milvus.latency_ms }} ms
                    </div>
                    <div v-if="milvus?.error" class="health-cell__error">{{ milvus.error }}</div>
                  </div>
                </div>
              </template>
            </YuxiCard>

            <!-- 检查时间 + trace_id -->
            <YuxiCard flat>
              <template #default>
                <div class="health-cell">
                  <div class="health-cell__icon">
                    <RefreshCw :size="20" />
                  </div>
                  <div class="health-cell__body">
                    <div class="health-cell__label">最近检查时间</div>
                    <div class="health-cell__value">{{ formatTime(healthData.timestamp) }}</div>
                    <div v-if="healthData.trace_id" class="health-cell__trace">
                      <span class="health-cell__trace-label">追踪编号</span>
                      <code class="health-cell__trace-id">{{ healthData.trace_id }}</code>
                    </div>
                  </div>
                </div>
              </template>
            </YuxiCard>
          </div>

          <!-- 应用与环境信息 -->
          <div class="dashboard__meta-row">
            <span class="dashboard__meta-tag">{{ healthData.app }}</span>
            <span class="dashboard__meta-tag dashboard__meta-tag--env">{{ healthData.env }}</span>
          </div>
        </section>

        <!-- ===== 错误状态 ===== -->
        <section v-else-if="hasError" class="dashboard__section">
          <YuxiCard flat>
            <template #default>
              <div class="dashboard__error">
                <div class="dashboard__error-icon">
                  <AlertTriangle :size="36" />
                </div>
                <div class="dashboard__error-title">后端服务连接失败</div>
                <div class="dashboard__error-desc">
                  {{ healthError || '请检查 API 地址或服务状态' }}
                </div>
                <Button type="primary" :loading="isLoading" @click="refresh">
                  <template #icon><RefreshCw :size="14" /></template>
                  重新检查
                </Button>
              </div>
            </template>
          </YuxiCard>
        </section>

        <!-- ===== 空态 ===== -->
        <section v-else-if="!isLoading" class="dashboard__section">
          <YuxiCard flat>
            <template #default>
              <div class="dashboard__idle">
                <div class="dashboard__idle-icon">
                  <ServerCog :size="40" />
                </div>
                <div class="dashboard__idle-title">尚未获取后端状态</div>
                <div class="dashboard__idle-desc">点击右上角"重新检查"以获取后端健康状态</div>
              </div>
            </template>
          </YuxiCard>
        </section>
      </Spin>

      <!-- ===== 第二行：快捷入口 ===== -->
      <section class="dashboard__section">
        <h2 class="dashboard__section-title">快捷入口</h2>
        <div class="dashboard__grid dashboard__grid--entry">
          <YuxiCard interactive>
            <template #default>
              <div class="entry-cell">
                <div class="entry-cell__icon">
                  <Library :size="20" />
                </div>
                <div class="entry-cell__body">
                  <div class="entry-cell__title">知识库</div>
                  <div class="entry-cell__desc">
                    创建和管理知识库、上传文档并构建向量索引
                  </div>
                </div>
                <div class="entry-cell__action">
                  <Button type="primary" @click="go('/knowledge-bases')">进入知识库</Button>
                </div>
              </div>
            </template>
          </YuxiCard>

          <YuxiCard interactive>
            <template #default>
              <div class="entry-cell">
                <div class="entry-cell__icon">
                  <MessageSquare :size="20" />
                </div>
                <div class="entry-cell__body">
                  <div class="entry-cell__title">聊天问答</div>
                  <div class="entry-cell__desc">
                    选择知识库进行 RAG 问答和引用来源查看
                  </div>
                </div>
                <div class="entry-cell__action">
                  <Button type="primary" @click="go('/chat')">开始问答</Button>
                </div>
              </div>
            </template>
          </YuxiCard>

          <YuxiCard interactive>
            <template #default>
              <div class="entry-cell">
                <div class="entry-cell__icon">
                  <Settings :size="20" />
                </div>
                <div class="entry-cell__body">
                  <div class="entry-cell__title">设置</div>
                  <div class="entry-cell__desc">
                    配置前端 API Base URL 并测试后端连接
                  </div>
                </div>
                <div class="entry-cell__action">
                  <Button type="primary" @click="go('/settings')">打开设置</Button>
                </div>
              </div>
            </template>
          </YuxiCard>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.dashboard__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 20px var(--kb-page-padding, 24px);
  max-width: 1200px;
}

.dashboard__section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dashboard__section-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.dashboard__grid {
  display: grid;
  gap: 12px;
}

.dashboard__grid--health {
  grid-template-columns: repeat(4, 1fr);
}

.dashboard__grid--entry {
  grid-template-columns: repeat(3, 1fr);
}

/* 健康单元格 */
.health-cell {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.health-cell__icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--yuxi-main-30);
  border: 1px solid var(--yuxi-gray-150);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--yuxi-main-color);
}

.health-cell__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.health-cell__label {
  font-size: 13px;
  color: var(--yuxi-gray-600);
  font-weight: 500;
}

.health-cell__value {
  font-size: 14px;
  color: var(--yuxi-gray-900);
  font-weight: 600;
}

.health-cell__meta {
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.health-cell__error {
  font-size: 12px;
  color: var(--yuxi-error-700);
  word-break: break-all;
}

.health-cell__trace {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.health-cell__trace-label {
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.health-cell__trace-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--yuxi-gray-700);
  background: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: 4px;
  padding: 1px 6px;
}

/* 元信息行 */
.dashboard__meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dashboard__meta-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  background: var(--yuxi-gray-100);
  color: var(--yuxi-gray-600);
  border-radius: 4px;
}

.dashboard__meta-tag--env {
  background: var(--yuxi-main-50);
  color: var(--yuxi-main-700);
}

/* 错误状态 */
.dashboard__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 0 24px;
  text-align: center;
}

.dashboard__error-icon {
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

.dashboard__error-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.dashboard__error-desc {
  font-size: 13px;
  color: var(--yuxi-gray-600);
  margin-bottom: 6px;
  text-align: center;
  max-width: 480px;
  word-break: break-all;
}

/* 空态 */
.dashboard__idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0 24px;
  text-align: center;
}

.dashboard__idle-icon {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--yuxi-gray-50);
  color: var(--yuxi-gray-400);
  margin-bottom: 6px;
}

.dashboard__idle-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.dashboard__idle-desc {
  font-size: 13px;
  color: var(--yuxi-gray-600);
}

/* 快捷入口单元格 */
.entry-cell {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.entry-cell__icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--yuxi-main-30);
  border: 1px solid var(--yuxi-gray-150);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--yuxi-main-color);
}

.entry-cell__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entry-cell__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.entry-cell__desc {
  font-size: 12px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
}

.entry-cell__action {
  flex-shrink: 0;
  align-self: flex-end;
}

/* 移动端：网格降为单/双列，不溢出 */
@media (max-width: 1023px) {
  .dashboard__grid--health {
    grid-template-columns: repeat(2, 1fr);
  }
  .dashboard__grid--entry {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 639px) {
  .dashboard__grid--health,
  .dashboard__grid--entry {
    grid-template-columns: 1fr;
  }
  .entry-cell {
    flex-direction: column;
  }
  .entry-cell__action {
    align-self: flex-start;
  }
}
</style>
