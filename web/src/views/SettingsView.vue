<script setup lang="ts">
/**
 * 设置页：配置后端 API 地址（P1.5 完善）
 * - 显示当前后端地址
 * - 测试连接：调用 GET /health，成功显示"连接正常"，失败显示中文错误 + 追踪编号
 * - 保存设置：写入 localStorage（key: ragent.apiBaseUrl）
 * - 恢复默认：清除 localStorage，恢复默认地址
 * - 不存储 API Key / 模型密钥
 */
import { ref } from 'vue'
import { Card, Form, FormItem, Input, Button, Space, Alert, message } from 'ant-design-vue'
import { Save, RotateCcw, Plug } from 'lucide-vue-next'
import {
  DEFAULT_API_BASE_URL,
  getApiBaseUrl,
  setApiBaseUrl,
  ApiError,
  NetworkError,
  formatApiError,
} from '@/api/client'
import { getHealthRaw } from '@/api/health'

const baseUrl = ref<string>(getApiBaseUrl())

/** 测试连接状态 */
const testing = ref<boolean>(false)
/** 测试连接结果：success / error + 中文文案 */
const testResult = ref<{ type: 'success' | 'error'; message: string } | null>(null)

function handleSave(): void {
  const trimmed = baseUrl.value.trim()
  if (!trimmed) {
    message.warning('请输入后端 API 地址')
    return
  }
  if (!/^https?:\/\//i.test(trimmed)) {
    message.warning('后端 API 地址必须以 http:// 或 https:// 开头')
    return
  }
  // 写入 localStorage 并刷新响应式值
  setApiBaseUrl(trimmed)
  baseUrl.value = getApiBaseUrl()
  message.success('设置已保存')
}

function handleReset(): void {
  localStorage.removeItem('ragent.apiBaseUrl')
  baseUrl.value = DEFAULT_API_BASE_URL
  testResult.value = null
  message.success('已恢复默认地址')
}

/** 测试连接：调用 GET /health，验证后端可达 */
async function handleTestConnection(): Promise<void> {
  const trimmed = baseUrl.value.trim()
  if (!trimmed) {
    message.warning('请输入后端 API 地址')
    return
  }
  if (!/^https?:\/\//i.test(trimmed)) {
    message.warning('后端 API 地址必须以 http:// 或 https:// 开头')
    return
  }
  // 临时写入以便测试连接使用最新地址
  setApiBaseUrl(trimmed)
  baseUrl.value = getApiBaseUrl()

  testing.value = true
  testResult.value = null
  try {
    const resp = await getHealthRaw()
    if (resp.code === 0) {
      testResult.value = { type: 'success', message: '连接正常' }
    } else {
      const trace = resp.trace_id ? `，追踪编号：${resp.trace_id}` : ''
      testResult.value = {
        type: 'error',
        message: `${resp.message || '连接失败'}${trace}`,
      }
    }
  } catch (err) {
    if (err instanceof NetworkError) {
      testResult.value = {
        type: 'error',
        message: '连接后端服务失败，请检查 API 地址或服务状态。',
      }
    } else if (err instanceof ApiError) {
      const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
      testResult.value = { type: 'error', message: `${err.message}${trace}` }
    } else {
      testResult.value = { type: 'error', message: formatApiError(err) }
    }
  } finally {
    testing.value = false
  }
}
</script>

<template>
  <div class="settings-view">
    <Card class="settings-view__card" :bordered="true">
      <template #title>系统设置</template>

      <Form layout="vertical" class="settings-view__form">
        <FormItem label="后端 API 地址">
          <Input
            v-model:value="baseUrl"
            placeholder="请输入后端 API 地址，例如 http://localhost:8000"
            allow-clear
          />
        </FormItem>
        <FormItem label="当前后端地址">
          <span class="settings-view__current">{{ baseUrl || '（未设置）' }}</span>
        </FormItem>

        <!-- 测试连接结果 -->
        <Alert
          v-if="testResult"
          :type="testResult.type"
          show-icon
          :message="testResult.message"
          class="settings-view__test-result"
        />

        <FormItem>
          <Space>
            <Button :loading="testing" @click="handleTestConnection">
              <template #icon><Plug :size="14" /></template>
              测试连接
            </Button>
            <Button type="primary" @click="handleSave">
              <template #icon><Save :size="14" /></template>
              保存设置
            </Button>
            <Button @click="handleReset">
              <template #icon><RotateCcw :size="14" /></template>
              恢复默认
            </Button>
          </Space>
        </FormItem>
      </Form>

      <div class="settings-view__tips">
        <p>说明：</p>
        <ul>
          <li>默认地址为 <code>{{ DEFAULT_API_BASE_URL }}</code>。</li>
          <li>前端所有请求将发往该地址。</li>
          <li>「测试连接」会调用 <code>GET /health</code> 验证后端可达性。</li>
          <li>修改后请点击「保存设置」以持久化，再前往「仪表盘」刷新状态。</li>
        </ul>
      </div>
    </Card>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 720px;
}

.settings-view__card {
  border-radius: var(--app-radius);
}

.settings-view__form {
  max-width: 520px;
}

.settings-view__current {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--app-text-secondary);
  font-size: 13px;
}

.settings-view__test-result {
  margin-bottom: 16px;
}

.settings-view__tips {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--app-border);
  color: var(--app-text-secondary);
  font-size: 13px;
}

.settings-view__tips ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.settings-view__tips code {
  background-color: #fafafa;
  border: 1px solid var(--app-border);
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 12px;
  color: var(--app-text);
}
</style>
