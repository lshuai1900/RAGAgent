/**
 * 文档 API 客户端
 * 对应后端：
 * - POST   /api/v1/documents/upload（multipart：kb_id + file）
 * - GET    /api/v1/documents（可按 kb_id 过滤）
 * - GET    /api/v1/documents/{document_id}（查询单个文档状态，用于轮询）
 * - PATCH  /api/v1/knowledge-bases/{kb_id}/documents/{document_id}（重命名）
 * - DELETE /api/v1/knowledge-bases/{kb_id}/documents/{document_id}（删除，同时删向量索引）
 * - POST   /api/v1/knowledge-bases/{kb_id}/documents/{document_id}/reprocess（重新处理）
 */
import { request } from './client'
import type {
  DocumentDeleteResponse,
  DocumentOut,
  DocumentPage,
  DocumentUpdate,
  DocumentUploadResponse,
} from '@/types/api'

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

/** 重命名文档（同一知识库内文件名唯一） */
export function updateDocument(
  kbId: string,
  documentId: string,
  data: DocumentUpdate,
): Promise<DocumentOut> {
  return request<DocumentOut>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'PATCH',
      body: data,
    },
  )
}

/** 删除文档（同时删除对应向量索引 + 分块元数据 + 文档记录） */
export function deleteDocument(
  kbId: string,
  documentId: string,
): Promise<DocumentDeleteResponse> {
  return request<DocumentDeleteResponse>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(documentId)}`,
    {
      method: 'DELETE',
    },
  )
}

/** 重新处理文档（删除旧向量 + 旧分块，重新 embedding + 索引） */
export function reprocessDocument(kbId: string, documentId: string): Promise<DocumentOut> {
  return request<DocumentOut>(
    `/api/v1/knowledge-bases/${encodeURIComponent(kbId)}/documents/${encodeURIComponent(documentId)}/reprocess`,
    {
      method: 'POST',
    },
  )
}
