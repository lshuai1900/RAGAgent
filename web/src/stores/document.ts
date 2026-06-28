/**
 * 文档 Pinia store
 * - 列表加载 / 上传 / 单文档状态轮询
 * - 不直接发 fetch，统一调 api 层
 * - 轮询：上传成功后每 2s 查 GET /api/v1/documents/{document_id}，
 *   状态进入 completed/failed 终态后停止；页面卸载调 stopAllPolling
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { formatApiError } from '@/api/client'
import {
  uploadDocument as apiUploadDocument,
  listDocuments as apiListDocuments,
  getDocument as apiGetDocument,
  updateDocument as apiUpdateDocument,
  deleteDocument as apiDeleteDocument,
  reprocessDocument as apiReprocessDocument,
} from '@/api/documents'
import { isTerminalDocumentStatus } from '@/utils/status'
import type {
  DocumentDeleteResponse,
  DocumentOut,
  DocumentPage,
  DocumentUpdate,
  DocumentUploadResponse,
} from '@/types/api'

export type LoadState = 'idle' | 'loading' | 'success' | 'error'

/** 轮询间隔（毫秒） */
const POLL_INTERVAL_MS = 2000

export const useDocumentStore = defineStore('document', () => {
  // ===== 列表 =====
  const list = ref<DocumentOut[]>([])
  const listState = ref<LoadState>('idle')
  const listError = ref<string>('')
  const total = ref<number>(0)
  let listAbort: AbortController | null = null

  /** 当前 store 绑定的知识库 ID（避免跨知识库污染） */
  const currentKbId = ref<string>('')

  async function fetchList(kbId: string): Promise<void> {
    currentKbId.value = kbId
    listAbort?.abort()
    listAbort = new AbortController()
    listState.value = 'loading'
    listError.value = ''
    try {
      const data: DocumentPage = await apiListDocuments({
        kb_id: kbId,
        page: 1,
        page_size: 100,
        signal: listAbort.signal,
      })
      list.value = data.items ?? []
      total.value = data.total ?? 0
      listState.value = 'success'
      // 对非终态文档恢复轮询
      resumePollingForNonTerminal()
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      list.value = []
      total.value = 0
      listState.value = 'error'
      listError.value = formatApiError(err)
    } finally {
      listAbort = null
    }
  }

  // ===== 上传 =====
  const uploading = ref<boolean>(false)
  const uploadError = ref<string>('')

  async function upload(
    kbId: string,
    file: File,
  ): Promise<DocumentUploadResponse> {
    uploading.value = true
    uploadError.value = ''
    try {
      const res = await apiUploadDocument(kbId, file)
      // 上传成功后刷新列表并启动该文档轮询
      await fetchList(kbId)
      startPolling(res.document_id)
      return res
    } catch (err) {
      uploadError.value = formatApiError(err)
      throw err
    } finally {
      uploading.value = false
    }
  }

  // ===== 单文档查询（操作列"刷新状态"） =====
  async function refreshDocument(documentId: string): Promise<void> {
    try {
      const doc = await apiGetDocument(documentId)
      upsertDocument(doc)
      if (!isTerminalDocumentStatus(doc.status)) {
        startPolling(documentId)
      }
    } catch (err) {
      // 操作列刷新失败不中断主流程，抛出由调用方提示
      throw err
    }
  }

  // ===== 重命名文档 =====
  const renaming = ref<boolean>(false)
  const renameError = ref<string>('')

  async function renameDocument(
    kbId: string,
    documentId: string,
    payload: DocumentUpdate,
  ): Promise<DocumentOut> {
    renaming.value = true
    renameError.value = ''
    try {
      const doc = await apiUpdateDocument(kbId, documentId, payload)
      // 同步更新列表中的该条记录（保持原顺序）
      upsertDocument(doc)
      return doc
    } catch (err) {
      renameError.value = formatApiError(err)
      throw err
    } finally {
      renaming.value = false
    }
  }

  // ===== 删除文档 =====
  const deleting = ref<boolean>(false)
  const deleteError = ref<string>('')

  async function deleteDocument(
    kbId: string,
    documentId: string,
  ): Promise<DocumentDeleteResponse> {
    deleting.value = true
    deleteError.value = ''
    try {
      const result = await apiDeleteDocument(kbId, documentId)
      // 从列表移除该文档，并同步 total
      const idx = list.value.findIndex((d) => d.id === documentId)
      if (idx >= 0) {
        list.value.splice(idx, 1)
        total.value = Math.max(0, total.value - 1)
      }
      // 停止该文档的轮询（如有）
      const timer = pollingTimers.get(documentId)
      if (timer) {
        clearTimeout(timer)
        pollingTimers.delete(documentId)
      }
      return result
    } catch (err) {
      deleteError.value = formatApiError(err)
      throw err
    } finally {
      deleting.value = false
    }
  }

  // ===== 重新处理文档 =====
  const reprocessing = ref<boolean>(false)
  const reprocessError = ref<string>('')

  async function reprocessDocument(
    kbId: string,
    documentId: string,
  ): Promise<DocumentOut> {
    reprocessing.value = true
    reprocessError.value = ''
    try {
      const doc = await apiReprocessDocument(kbId, documentId)
      // 同步更新列表中的该条记录（状态变为 embedding）
      upsertDocument(doc)
      // 启动轮询，直到进入终态
      if (!isTerminalDocumentStatus(doc.status)) {
        startPolling(documentId)
      }
      return doc
    } catch (err) {
      reprocessError.value = formatApiError(err)
      throw err
    } finally {
      reprocessing.value = false
    }
  }

  /** 更新或插入单条文档到列表（保持原顺序） */
  function upsertDocument(doc: DocumentOut): void {
    const idx = list.value.findIndex((d) => d.id === doc.id)
    if (idx >= 0) {
      list.value[idx] = doc
    } else {
      list.value.unshift(doc)
      total.value += 1
    }
  }

  // ===== 轮询 =====
  /** 正在轮询的 documentId -> 定时器 */
  const pollingTimers = new Map<string, ReturnType<typeof setTimeout>>()

  /** 启动单个文档的轮询（重复启动同一文档会被忽略，避免无限轮询） */
  function startPolling(documentId: string): void {
    if (pollingTimers.has(documentId)) return
    const tick = async (): Promise<void> => {
      try {
        const doc = await apiGetDocument(documentId)
        upsertDocument(doc)
        if (isTerminalDocumentStatus(doc.status)) {
          pollingTimers.delete(documentId)
          return
        }
      } catch {
        // 轮询单次失败即停止该文档轮询，避免无限重试
        pollingTimers.delete(documentId)
        return
      }
      pollingTimers.set(documentId, setTimeout(tick, POLL_INTERVAL_MS))
    }
    pollingTimers.set(documentId, setTimeout(tick, POLL_INTERVAL_MS))
  }

  /** 对列表中所有非终态文档恢复轮询（用于列表加载后） */
  function resumePollingForNonTerminal(): void {
    for (const doc of list.value) {
      if (!isTerminalDocumentStatus(doc.status)) {
        startPolling(doc.id)
      }
    }
  }

  /** 停止所有轮询（页面卸载时调用） */
  function stopAllPolling(): void {
    pollingTimers.forEach((timer) => clearTimeout(timer))
    pollingTimers.clear()
  }

  /** 重置 store（切换知识库 / 离开页面时调用） */
  function reset(): void {
    listAbort?.abort()
    stopAllPolling()
    list.value = []
    total.value = 0
    listState.value = 'idle'
    listError.value = ''
    uploading.value = false
    uploadError.value = ''
    renaming.value = false
    renameError.value = ''
    deleting.value = false
    deleteError.value = ''
    reprocessing.value = false
    reprocessError.value = ''
    currentKbId.value = ''
  }

  return {
    // 列表
    list,
    listState,
    listError,
    total,
    currentKbId,
    fetchList,
    // 上传
    uploading,
    uploadError,
    upload,
    // 单文档
    refreshDocument,
    // 重命名
    renaming,
    renameError,
    renameDocument,
    // 删除
    deleting,
    deleteError,
    deleteDocument,
    // 重新处理
    reprocessing,
    reprocessError,
    reprocessDocument,
    // 轮询
    startPolling,
    stopAllPolling,
    // 重置
    reset,
  }
})
