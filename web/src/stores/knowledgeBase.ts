/**
 * 知识库 Pinia store
 * - 列表加载 / 创建 / 详情查询
 * - 不直接发 fetch，统一调 api 层
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { formatApiError } from '@/api/client'
import {
  createKnowledgeBase as apiCreateKb,
  deleteKnowledgeBase as apiDeleteKb,
  getKnowledgeBase as apiGetKb,
  listKnowledgeBases as apiListKbs,
  updateKnowledgeBase as apiUpdateKb,
} from '@/api/knowledgeBases'
import type {
  KnowledgeBaseCreate,
  KnowledgeBaseDeleteResponse,
  KnowledgeBaseOut,
  KnowledgeBasePage,
  KnowledgeBaseUpdate,
} from '@/types/api'

export type LoadState = 'idle' | 'loading' | 'success' | 'error'

export const useKnowledgeBaseStore = defineStore('knowledgeBase', () => {
  // ===== 列表 =====
  const list = ref<KnowledgeBaseOut[]>([])
  const listState = ref<LoadState>('idle')
  const listError = ref<string>('')
  const total = ref<number>(0)
  let listAbort: AbortController | null = null

  async function fetchList(page = 1, pageSize = 50): Promise<void> {
    listAbort?.abort()
    listAbort = new AbortController()
    listState.value = 'loading'
    listError.value = ''
    try {
      const data: KnowledgeBasePage = await apiListKbs({
        page,
        page_size: pageSize,
        signal: listAbort.signal,
      })
      list.value = data.items ?? []
      total.value = data.total ?? 0
      listState.value = 'success'
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

  // ===== 创建 =====
  const creating = ref<boolean>(false)
  const createError = ref<string>('')

  async function createKb(payload: KnowledgeBaseCreate): Promise<KnowledgeBaseOut> {
    creating.value = true
    createError.value = ''
    try {
      const kb = await apiCreateKb(payload)
      // 创建成功后刷新列表
      await fetchList()
      return kb
    } catch (err) {
      createError.value = formatApiError(err)
      throw err
    } finally {
      creating.value = false
    }
  }

  // ===== 更新 =====
  const updating = ref<boolean>(false)
  const updateError = ref<string>('')

  async function updateKb(kbId: string, payload: KnowledgeBaseUpdate): Promise<KnowledgeBaseOut> {
    updating.value = true
    updateError.value = ''
    try {
      const kb = await apiUpdateKb(kbId, payload)
      // 同步更新详情缓存（标题立即变化）
      detail.value = kb
      // 刷新列表缓存（名称/描述同步）
      await fetchList()
      return kb
    } catch (err) {
      updateError.value = formatApiError(err)
      throw err
    } finally {
      updating.value = false
    }
  }

  // ===== 删除 =====
  const deleting = ref<boolean>(false)
  const deleteError = ref<string>('')

  async function deleteKb(kbId: string): Promise<KnowledgeBaseDeleteResponse> {
    deleting.value = true
    deleteError.value = ''
    try {
      const result = await apiDeleteKb(kbId)
      // 清空详情缓存并刷新列表（archived 不再返回）
      detail.value = null
      detailState.value = 'idle'
      detailError.value = ''
      await fetchList()
      return result
    } catch (err) {
      deleteError.value = formatApiError(err)
      throw err
    } finally {
      deleting.value = false
    }
  }

  // ===== 详情 =====
  const detail = ref<KnowledgeBaseOut | null>(null)
  const detailState = ref<LoadState>('idle')
  const detailError = ref<string>('')
  let detailAbort: AbortController | null = null

  async function fetchDetail(kbId: string): Promise<void> {
    detailAbort?.abort()
    detailAbort = new AbortController()
    detailState.value = 'loading'
    detailError.value = ''
    detail.value = null
    try {
      detail.value = await apiGetKb(kbId, detailAbort.signal)
      detailState.value = 'success'
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return
      detail.value = null
      detailState.value = 'error'
      detailError.value = formatApiError(err)
    } finally {
      detailAbort = null
    }
  }

  function resetDetail(): void {
    detailAbort?.abort()
    detail.value = null
    detailState.value = 'idle'
    detailError.value = ''
  }

  return {
    // 列表
    list,
    listState,
    listError,
    total,
    fetchList,
    // 创建
    creating,
    createError,
    createKb,
    // 更新
    updating,
    updateError,
    updateKb,
    // 删除
    deleting,
    deleteError,
    deleteKb,
    // 详情
    detail,
    detailState,
    detailError,
    fetchDetail,
    resetDetail,
  }
})
