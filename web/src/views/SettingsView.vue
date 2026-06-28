<script setup lang="ts">
/**
 * 设置页：配置后端 API 地址
 * - 显示当前后端地址
 * - 支持修改、保存、恢复默认
 * - 保存到 localStorage
 */
import { ref } from 'vue'
import { Card, Form, FormItem, Input, Button, Space, message } from 'ant-design-vue'
import { Save, RotateCcw } from 'lucide-vue-next'
import { DEFAULT_API_BASE_URL, getApiBaseUrl } from '@/api/client'

const baseUrl = ref<string>(getApiBaseUrl())

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
  localStorage.setItem('ragent.apiBaseUrl', trimmed.replace(/\/+$/, ''))
  baseUrl.value = trimmed.replace(/\/+$/, '')
  message.success('设置已保存')
}

function handleReset(): void {
  localStorage.removeItem('ragent.apiBaseUrl')
  baseUrl.value = DEFAULT_API_BASE_URL
  message.success('已恢复默认地址')
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
        <FormItem>
          <Space>
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
          <li>修改后请前往「仪表盘」刷新状态以验证连接。</li>
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
