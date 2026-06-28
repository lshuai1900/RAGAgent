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
  getKnowledgeBase as apiGetKb,
  listKnowledgeBases as apiListKbs,
} from '@/api/knowledgeBases'
import type { KnowledgeBaseCreate, KnowledgeBaseOut, KnowledgeBasePage } from '@/types/api'

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
    // 详情
    detail,
    detailState,
    detailError,
    fetchDetail,
    resetDetail,
  }
})
