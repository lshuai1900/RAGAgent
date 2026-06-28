/**
 * 文档 API 客户端
 * 对应后端：
 * - POST /api/v1/documents/upload（multipart：kb_id + file）
 * - GET  /api/v1/documents（可按 kb_id 过滤）
 * - GET  /api/v1/documents/{document_id}（查询单个文档状态，用于轮询）
 */
import { request } from './client'
import type { DocumentOut, DocumentPage, DocumentUploadResponse } from '@/types/api'

/** 上传文档（multipart/form-data），立即返回 document_id */
export function uploadDocument(
  kbId: string,
  file: File,
  signal?: AbortSignal,
): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('kb_id', kbId)
  formData.append('file', file)
  // 不手设 Content-Type，由 client.ts 透传 FormData，浏览器自动加 boundary
  return request<DocumentUploadResponse>('/api/v1/documents/upload', {
    method: 'POST',
    body: formData,
    signal,
  })
}

/** 分页列出文档（可按 kb_id 过滤） */
export function listDocuments(params?: {
  kb_id?: string
  page?: number
  page_size?: number
  signal?: AbortSignal
}): Promise<DocumentPage> {
  return request<DocumentPage>('/api/v1/documents', {
    method: 'GET',
    query: { kb_id: params?.kb_id, page: params?.page, page_size: params?.page_size },
    signal: params?.signal,
  })
}

/** 查询单个文档状态（轮询用） */
export function getDocument(documentId: string, signal?: AbortSignal): Promise<DocumentOut> {
  return request<DocumentOut>(`/api/v1/documents/${encodeURIComponent(documentId)}`, {
    method: 'GET',
    signal,
  })
}
