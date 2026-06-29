/**
 * 引用来源归一化工具（Step 7）
 *
 * 后端 SSE done 事件可能下发：
 * - references：已是引用来源数组（优先使用）
 * - citations：需映射为 references
 * - retrieval_context：旧字段，向后兼容
 *
 * 本工具把上述任一字段统一归一化为 UiChatReference[]，供前端 UI 消费。
 * 不伪造引用来源；三者均缺失时返回空数组。
 */

/** 前端统一的引用来源类型 */
export interface UiChatReference {
  /** 文档编号 */
  documentId?: string
  /** 文档名称 */
  documentName?: string
  /** 文件名 */
  filename?: string
  /** 内容摘要 */
  content?: string
  /** 相似度分数（0-1） */
  score?: number
  /** 分块编号 */
  chunkId?: string
  /** 原始元数据（透传后端扩展字段） */
  metadata?: Record<string, unknown>
}

/** done 事件中可能携带引用来源的载荷（任一即可） */
export interface ReferenceSourcePayload {
  references?: unknown
  citations?: unknown
  retrieval_context?: unknown
}

/**
 * 把单条原始引用对象归一化为 UiChatReference。
 * 字段别名兼容后端多种命名。
 */
function normalizeOne(raw: unknown): UiChatReference | null {
  if (!raw || typeof raw !== 'object') return null
  const o = raw as Record<string, unknown>

  const ref: UiChatReference = {}

  // 文档编号
  const documentId = pickStr(o, 'document_id', 'doc_id')
  if (documentId) ref.documentId = documentId

  // 文档名称 / 文件名
  const documentName = pickStr(o, 'document_name', 'source')
  if (documentName) ref.documentName = documentName
  const filename = pickStr(o, 'filename', 'file_name', 'source')
  if (filename) ref.filename = filename

  // 内容摘要
  const content = pickStr(o, 'content', 'text', 'chunk_text', 'snippet')
  if (content) ref.content = content

  // 相似度分数（字符串也尝试转 number）
  const score = pickNumber(o, 'score', 'similarity')
  if (score !== undefined) ref.score = score

  // 分块编号
  const chunkId = pickStr(o, 'chunk_id', 'chunkId')
  if (chunkId) ref.chunkId = chunkId

  // 元数据透传
  if (o.metadata && typeof o.metadata === 'object') {
    ref.metadata = o.metadata as Record<string, unknown>
  }

  return ref
}

/**
 * 从 done 载荷中提取并归一化引用来源列表。
 *
 * 优先级：references > citations > retrieval_context
 * - references 存在且为数组：直接归一化
 * - citations 存在且为数组：映射为 references
 * - retrieval_context 存在且为数组：向后兼容
 * - 均缺失：返回空数组
 */
export function mapCitationsToReferences(
  payload: ReferenceSourcePayload | unknown,
): UiChatReference[] {
  if (!payload || typeof payload !== 'object') return []
  const p = payload as ReferenceSourcePayload

  const rawList = pickArray(p.references) ?? pickArray(p.citations) ?? pickArray(p.retrieval_context)
  if (!rawList) return []

  const result: UiChatReference[] = []
  for (const raw of rawList) {
    const ref = normalizeOne(raw)
    if (ref) result.push(ref)
  }
  return result
}

/** 取字符串字段（按优先级顺序，返回第一个非空字符串） */
function pickStr(o: Record<string, unknown>, ...keys: string[]): string | undefined {
  for (const k of keys) {
    const v = o[k]
    if (typeof v === 'string' && v.trim() !== '') return v
  }
  return undefined
}

/** 取数值字段（字符串也尝试转换） */
function pickNumber(o: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const k of keys) {
    const v = o[k]
    if (typeof v === 'number' && Number.isFinite(v)) return v
    if (typeof v === 'string' && v.trim() !== '') {
      const n = Number(v)
      if (Number.isFinite(n)) return n
    }
  }
  return undefined
}

/** 取数组字段 */
function pickArray(v: unknown): unknown[] | null {
  if (Array.isArray(v)) return v as unknown[]
  return null
}
