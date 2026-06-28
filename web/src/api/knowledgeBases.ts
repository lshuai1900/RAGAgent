/**
 * 知识库 API 客户端
 * 对应后端：
 * - POST   /api/v1/knowledge-bases
 * - GET    /api/v1/knowledge-bases
 * - GET    /api/v1/knowledge-bases/{kb_id}
 * - PATCH  /api/v1/knowledge-bases/{kb_id}
 * - DELETE /api/v1/knowledge-bases/{kb_id}
 */
import { request } from './client'
import type {
  KnowledgeBaseCreate,
  KnowledgeBaseDeleteResponse,
  KnowledgeBaseOut,
  KnowledgeBasePage,
  KnowledgeBaseUpdate,
} from '@/types/api'

/** 分页列出知识库 */
export function listKnowledgeBases(params?: {
  page?: number
  page_size?: number
  signal?: AbortSignal
}): Promise<KnowledgeBasePage> {
  return request<KnowledgeBasePage>('/api/v1/knowledge-bases', {
    method: 'GET',
    query: { page: params?.page, page_size: params?.page_size },
    signal: params?.signal,
  })
}

/** 创建知识库 */
export function createKnowledgeBase(payload: KnowledgeBaseCreate): Promise<KnowledgeBaseOut> {
  return request<KnowledgeBaseOut>('/api/v1/knowledge-bases', {
    method: 'POST',
    body: payload,
  })
}

/** 查询单个知识库详情 */
export function getKnowledgeBase(kbId: string, signal?: AbortSignal): Promise<KnowledgeBaseOut> {
  return request<KnowledgeBaseOut>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}`, {
    method: 'GET',
    signal,
  })
}

/** 更新知识库（重命名 / 描述 / 状态，部分更新） */
export function updateKnowledgeBase(
  kbId: string,
  payload: KnowledgeBaseUpdate,
): Promise<KnowledgeBaseOut> {
  return request<KnowledgeBaseOut>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}`, {
    method: 'PATCH',
    body: payload,
  })
}

/** 删除知识库（软删除：归档 + 尝试清理向量库 collection） */
export function deleteKnowledgeBase(kbId: string): Promise<KnowledgeBaseDeleteResponse> {
  return request<KnowledgeBaseDeleteResponse>(`/api/v1/knowledge-bases/${encodeURIComponent(kbId)}`, {
    method: 'DELETE',
  })
}
