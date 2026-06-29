<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 6：Yuxi 风格 dropzone + 文件预览 + 格式/大小/重名校验 + HTTP 错误映射。
-->
<script setup lang="ts">
/**
 * 文档上传弹窗（Step 6 / Yuxi 风格）
 *
 * - 单文件上传：拖拽或点击选择
 * - 格式校验：.txt / .md / .markdown / .pdf（大小写不敏感）
 * - 大小校验：≤ 50MB
 * - 重名检测：与当前知识库已有文档名比较（大小写不敏感、trim 后比较），重名阻止上传
 * - 上传状态：idle / uploading / success / error
 * - 成功后 emit('uploaded')，父组件启动列表轮询
 * - 失败保留面板 + 已选文件 + 中文错误 + trace_id
 *
 * 上传通过 api/documents.ts 封装（FormData 携带 kb_id），不在组件内写 fetch。
 * 后端返回 DocumentUploadResponse（含 document_id + duplicated 布尔）。
 */
import { computed, ref, watch } from 'vue'
import { Modal, UploadDragger, Button, message } from 'ant-design-vue'
import type { UploadProps } from 'ant-design-vue'
import { UploadCloud, CheckCircle2, AlertCircle, X } from 'lucide-vue-next'
import { ApiError, NetworkError, formatApiError } from '@/api/client'
import { useDocumentStore } from '@/stores/document'
import { formatFileSize } from '@/utils/format'
import { fileTypeText } from '@/utils/status'
import FileTypeIcon from '@/components/FileTypeIcon.vue'
import type { DocumentUploadResponse } from '@/types/api'

interface Props {
  open: boolean
  kbId: string
}
const props = defineProps<Props>()

interface Emits {
  (e: 'update:open', open: boolean): void
  (e: 'uploaded'): void
}
const emit = defineEmits<Emits>()

const docStore = useDocumentStore()

/** 文件大小上限：50MB（与后端一致） */
const MAX_FILE_SIZE = 50 * 1024 * 1024
/** 允许的扩展名（小写，含点） */
const ACCEPT_EXT = ['.txt', '.md', '.markdown', '.pdf']
/** input accept 属性 */
const ACCEPT_ATTR = '.txt,.md,.markdown,.pdf'

type Phase = 'idle' | 'uploading' | 'success' | 'error'

const phase = ref<Phase>('idle')
const selectedFile = ref<File | null>(null)
const errorMsg = ref<string>('')
const result = ref<DocumentUploadResponse | null>(null)
/** 拖拽悬停状态（用于高亮 dropzone） */
const isDragOver = ref(false)

const isUploading = computed(() => phase.value === 'uploading')

/** 当前知识库已有文件名集合（小写、trim） */
const existingNamesLower = computed<Set<string>>(
  () => new Set(docStore.list.map((d) => d.name.trim().toLowerCase())),
)

/** 选中的文件是否与已有文件重名 */
const isDuplicate = computed<boolean>(() => {
  if (!selectedFile.value) return false
  return existingNamesLower.value.has(selectedFile.value.name.trim().toLowerCase())
})

/** 校验错误（格式 / 大小 / 重名），用于禁用上传按钮 + 行内提示 */
const validationError = computed<string>(() => {
  if (!selectedFile.value) return ''
  const ext = getExt(selectedFile.value.name)
  if (!ACCEPT_EXT.includes(ext)) {
    return '当前仅支持 TXT、Markdown 和 PDF 文档'
  }
  if (selectedFile.value.size > MAX_FILE_SIZE) {
    return '单个文件不能超过 50MB'
  }
  if (isDuplicate.value) {
    return '当前知识库中已存在同名文件，请重命名后再上传'
  }
  return ''
})

/** 是否可点击"开始上传"：已选文件 + 无校验错误 + 非上传中 */
const canUpload = computed(
  () =>
    phase.value === 'idle' &&
    !!selectedFile.value &&
    !isUploading.value &&
    validationError.value === '',
)

/** 弹窗打开时重置状态 */
watch(
  () => props.open,
  (open) => {
    if (open) {
      phase.value = 'idle'
      selectedFile.value = null
      errorMsg.value = ''
      result.value = null
      isDragOver.value = false
    }
  },
)

/** 取文件扩展名（小写，含点） */
function getExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

/**
 * beforeUpload：拦截选择，做格式 / 大小 / 重名校验，阻止 Antd 自动上传。
 * 仅暂存文件，等用户点击"开始上传"。
 */
const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const ext = getExt(file.name)
  if (!ACCEPT_EXT.includes(ext)) {
    message.error('当前仅支持 TXT、Markdown 和 PDF 文档')
    selectedFile.value = null
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    message.error(`单个文件不能超过 50MB（当前：${formatFileSize(file.size)}）`)
    selectedFile.value = null
    return false
  }
  // 重名检测（基于当前已有列表）：仅暂存 + 行内提示，不弹 message（避免与行内提示重复）
  selectedFile.value = file
  errorMsg.value = ''
  result.value = null
  return false
}

/** 拖拽悬停 */
function handleDragEnter(): void {
  if (!isUploading.value) isDragOver.value = true
}
function handleDragLeave(e: DragEvent): void {
  // 仅当离开整个 dropzone 容器时才重置
  if (e.currentTarget === e.target) {
    isDragOver.value = false
  }
}
function handleDrop(): void {
  isDragOver.value = false
}

/** 上传错误映射（中文） */
function mapUploadError(err: unknown): string {
  if (err instanceof NetworkError) {
    return '无法连接后端服务，请检查 API 地址或服务状态'
  }
  if (err instanceof ApiError) {
    if (err.httpStatus === 400) return '上传参数不正确，请检查文件后重试'
    if (err.httpStatus === 409)
      return '当前知识库中已存在同名文件，请重命名后再上传'
    if (err.httpStatus === 413) return '文件过大，请上传不超过 50MB 的文件'
    if (err.httpStatus === 415) return '当前文件格式不支持'
    if (err.httpStatus >= 500) return '服务器内部错误，请稍后重试'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return formatApiError(err)
}

async function handleUpload(): Promise<void> {
  if (!selectedFile.value || isUploading.value) return
  // 上传前再次校验（防止用户在选文件后、点上传前的间隙列表刷新）
  if (validationError.value) {
    message.error(validationError.value)
    return
  }
  phase.value = 'uploading'
  errorMsg.value = ''
  result.value = null
  try {
    const res = await docStore.upload(props.kbId, selectedFile.value)
    result.value = res
    phase.value = 'success'
    if (res.duplicated) {
      message.success('文件内容已存在，已复用已有文档')
    } else {
      message.success('文档上传成功，正在处理')
    }
    emit('uploaded')
  } catch (err) {
    phase.value = 'error'
    errorMsg.value = mapUploadError(err)
  }
}

function handleClose(): void {
  emit('update:open', false)
}

/** 移除已选文件，回到 dropzone */
function handleClearFile(): void {
  selectedFile.value = null
  errorMsg.value = ''
  result.value = null
  phase.value = 'idle'
}

/** 失败后重试：保留已选文件，回到 idle 让用户再次点击上传 */
function handleRetry(): void {
  phase.value = 'idle'
  errorMsg.value = ''
  result.value = null
}

/** 文件类型展示文案 */
const fileTypeLabel = computed(() => {
  if (!selectedFile.value) return ''
  const ext = selectedFile.value.name.split('.').pop() ?? ''
  return fileTypeText(ext)
})
</script>

<template>
  <Modal
    :open="open"
    title="上传文档"
    :width="560"
    :mask-closable="false"
    :destroy-on-close="true"
    :footer="null"
    @cancel="handleClose"
  >
    <!-- 描述 -->
    <p class="upload-desc">
      支持 TXT、Markdown、PDF 文档，上传后将自动解析、分块、向量化并建立索引
    </p>

    <!-- 选择 / 上传中 -->
    <div v-if="phase === 'idle' || phase === 'uploading'">
      <!-- dropzone（仅未选文件时展示） -->
      <UploadDragger
        v-if="!selectedFile"
        :before-upload="beforeUpload"
        :show-upload-list="false"
        :multiple="false"
        :disabled="isUploading"
        :accept="ACCEPT_ATTR"
        class="upload-dragger"
        :class="{ 'upload-dragger--dragover': isDragOver }"
        @dragenter="handleDragEnter"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
      >
        <div class="dropzone">
          <UploadCloud :size="40" class="dropzone__icon" />
          <p class="dropzone__title">点击或将文件拖拽到此处上传</p>
          <p class="dropzone__hint">支持 .txt、.md、.markdown、.pdf，单文件最大 50MB</p>
        </div>
      </UploadDragger>

      <!-- 已选文件预览 -->
      <div
        v-if="selectedFile"
        class="file-preview"
        :class="{ 'file-preview--error': Boolean(validationError) }"
      >
        <FileTypeIcon :file-type="selectedFile.name.split('.').pop() ?? ''" :size="40" />
        <div class="file-preview__info">
          <span class="file-preview__name" :title="selectedFile.name">
            {{ selectedFile.name }}
          </span>
          <span class="file-preview__meta">
            {{ fileTypeLabel }} · {{ formatFileSize(selectedFile.size) }}
          </span>
        </div>
        <button
          v-if="!isUploading"
          type="button"
          class="file-preview__clear"
          title="移除文件"
          @click="handleClearFile"
        >
          <X :size="16" />
        </button>
      </div>

      <!-- 校验错误行内提示 -->
      <div v-if="validationError" class="upload-validation-error">
        <AlertCircle :size="14" />
        <span>{{ validationError }}</span>
      </div>
    </div>

    <!-- 上传成功 -->
    <div v-else-if="phase === 'success' && result" class="upload-result">
      <div class="upload-result__icon upload-result__icon--success">
        <CheckCircle2 :size="36" />
      </div>
      <p class="upload-result__title">文档上传成功，正在处理</p>
      <div class="upload-result__doc-id">
        <span class="upload-result__doc-id-label">文档编号：</span>
        <span class="upload-result__doc-id-value">{{ result.document_id }}</span>
      </div>
      <p v-if="result.duplicated" class="upload-result__dup">
        该文件内容已存在，已复用已有文档，无需重复上传。
      </p>
      <p class="upload-result__tip">
        文档将在后台进行解析、分块、向量化与入库，可在列表中查看状态变化。
      </p>
    </div>

    <!-- 上传失败 -->
    <div v-else-if="phase === 'error'" class="upload-result">
      <div class="upload-result__icon upload-result__icon--error">
        <AlertCircle :size="36" />
      </div>
      <p class="upload-result__title">上传失败</p>
      <p class="upload-result__error-msg">{{ errorMsg }}</p>
    </div>

    <!-- 底部按钮 -->
    <div class="upload-footer">
      <template v-if="phase === 'success'">
        <Button type="primary" @click="handleClose">关闭</Button>
      </template>
      <template v-else-if="phase === 'error'">
        <Button @click="handleClose">关闭</Button>
        <Button type="primary" @click="handleRetry">重新上传</Button>
      </template>
      <template v-else>
        <Button :disabled="isUploading" @click="handleClose">取消</Button>
        <Button
          type="primary"
          :loading="isUploading"
          :disabled="!canUpload"
          @click="handleUpload"
        >
          开始上传
        </Button>
      </template>
    </div>
  </Modal>
</template>

<style scoped>
/* 描述文案 */
.upload-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
}

/* ===== dropzone（覆盖 Antd UploadDragger 内部样式） ===== */
.upload-dragger :deep(.ant-upload-drag) {
  background: var(--yuxi-gray-25);
  border: 1.5px dashed var(--yuxi-gray-300);
  border-radius: var(--yuxi-radius);
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.upload-dragger :deep(.ant-upload-drag):hover {
  border-color: var(--yuxi-main-400);
  background: var(--yuxi-main-30);
}

.upload-dragger--dragover :deep(.ant-upload-drag) {
  border-color: var(--yuxi-main-color);
  background: var(--yuxi-main-50);
  box-shadow: 0 0 0 3px var(--yuxi-main-50);
}

.upload-dragger :deep(.ant-upload-btn) {
  padding: 0;
}

.dropzone {
  padding: 36px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.dropzone__icon {
  color: var(--yuxi-main-300);
}

.dropzone__title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--yuxi-gray-800);
}

.dropzone__hint {
  margin: 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

/* ===== 已选文件预览卡片 ===== */
.file-preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.file-preview--error {
  border-color: var(--yuxi-error-500);
  background: var(--yuxi-error-50);
}

.file-preview__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-preview__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--yuxi-gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview__meta {
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.file-preview__clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--yuxi-radius-sm);
  background: transparent;
  color: var(--yuxi-gray-400);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  flex-shrink: 0;
}

.file-preview__clear:hover {
  background: var(--yuxi-gray-100);
  color: var(--yuxi-error-700);
}

/* ===== 校验错误行内提示 ===== */
.upload-validation-error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: var(--yuxi-radius-sm);
  background: var(--yuxi-error-50);
  border: 1px solid var(--yuxi-error-500);
  color: var(--yuxi-error-700);
  font-size: 12px;
  line-height: 1.4;
}

/* ===== 结果区（成功 / 失败） ===== */
.upload-result {
  padding: 24px 0 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-result__icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.upload-result__icon--success {
  background: var(--yuxi-success-50);
  color: var(--yuxi-success-700);
}

.upload-result__icon--error {
  background: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
}

.upload-result__title {
  margin: 4px 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.upload-result__doc-id {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  background: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
  font-size: 13px;
}

.upload-result__doc-id-label {
  color: var(--yuxi-gray-500);
}

.upload-result__doc-id-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--yuxi-gray-700);
}

.upload-result__dup {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--yuxi-warning-700);
}

.upload-result__tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
  text-align: center;
  max-width: 400px;
}

.upload-result__error-msg {
  margin: 0;
  font-size: 13px;
  color: var(--yuxi-error-700);
  text-align: center;
  word-break: break-all;
  max-width: 440px;
  line-height: 1.5;
}

/* ===== 底部按钮 ===== */
.upload-footer {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ===== 移动端 ===== */
@media (max-width: 575px) {
  .dropzone {
    padding: 24px 12px;
  }
  .file-preview {
    padding: 10px 12px;
    gap: 10px;
  }
}
</style>
