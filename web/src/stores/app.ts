/**
 * 应用级 Pinia store
 * - 管理 apiBaseUrl（同步 localStorage）
 * - 管理健康检查状态（供仪表盘使用）
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  DEFAULT_API_BASE_URL,
  getApiBaseUrl,
  setApiBaseUrl,
  ApiError,
  NetworkError,
} from '@/api/client'
import { getHealth } from '@/api/health'
import type { HealthResponse } from '@/types/api'

export type HealthState = 'idle' | 'loading' | 'success' | 'error'

export const useAppStore = defineStore('app', () => {
  /** 当前 API Base URL（响应式，与 localStorage 同步） */
  const apiBaseUrl = ref<string>(getApiBaseUrl())

  /** 是否使用默认地址 */
  const isDefaultBaseUrl = computed(() => apiBaseUrl.value === DEFAULT_API_BASE_URL)

  /** 保存 API Base URL */
  function saveApiBaseUrl(url: string): void {
    setApiBaseUrl(url)
    apiBaseUrl.value = url.trim() ? url.trim().replace(/\/+$/, '') : DEFAULT_API_BASE_URL
  }

  /** 恢复默认 API Base URL */
  function resetApiBaseUrl(): void {
    setApiBaseUrl('')
    apiBaseUrl.value = DEFAULT_API_BASE_URL
  }

  // ===== 健康检查状态 =====
  const healthState = ref<HealthState>('idle')
  const healthData = ref<HealthResponse | null>(null)
  const healthError = ref<string>('')
  /** 进行中的请求 AbortController，用于取消 */
  let healthAbort: AbortController | null = null

  /** 拉取健康检查 */
  async function fetchHealth(): Promise<void> {
    // 取消上一个请求
    healthAbort?.abort()
    healthAbort = new AbortController()

    healthState.value = 'loading'
    healthError.value = ''
    try {
      const data = await getHealth(healthAbort.signal)
      healthData.value = data
      healthState.value = 'success'
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      healthData.value = null
      healthState.value = 'error'
      if (err instanceof NetworkError) {
        healthError.value = '后端服务连接失败，请检查 API 地址或服务状态'
      } else if (err instanceof ApiError) {
        const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
        healthError.value = `${err.message}${trace}`
      } else {
        healthError.value = '健康检查失败，请稍后重试'
      }
    } finally {
      healthAbort = null
    }
  }

  return {
    apiBaseUrl,
    isDefaultBaseUrl,
    saveApiBaseUrl,
    resetApiBaseUrl,
    healthState,
    healthData,
    healthError,
    fetchHealth,
  }
})
