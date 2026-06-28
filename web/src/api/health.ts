/**
 * 健康检查 API 客户端
 * 对应后端：GET /health
 */
import { request } from './client'
import type { ApiResponse, HealthResponse } from '@/types/api'

/** 健康检查：返回 HealthResponse */
export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return request<HealthResponse>('/health', { method: 'GET', signal })
}

/** 健康检查（返回完整 ApiResponse，用于设置页"测试连接"） */
export function getHealthRaw(signal?: AbortSignal): Promise<ApiResponse<HealthResponse>> {
  return request<HealthResponse>('/health', { method: 'GET', raw: true, signal })
}
