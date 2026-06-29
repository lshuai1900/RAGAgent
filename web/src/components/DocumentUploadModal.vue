<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.

  Step 6：上传面板 Yuxi 风格复刻。
  - 原生拖拽区（dragenter / dragover / dragleave / drop），不依赖 Antd UploadDragger
  - 隐藏 input[type=file] 处理点击选择
  - 单文件上传：input 不开 multiple；拖入多文件仅取第一个并提示
  - 三层校验：扩展名 / 大小（50MB）/ 同名（基于 existingNames prop）
  - 校验失败显示行内红色提示，不发请求
  - 上传中禁用关闭与重复提交
  - 错误码映射：NetworkError / 400 / 409 / 413 / 415 / 5xx
  - trace_id 如有则展示
  - 上传成功 emit('uploaded') 由父组件重启列表轮询
-->
<script setup lang="ts">
/**
 * 上传文档弹窗（Yuxi 风格）
 *
 * 结构：
 * - header：标题 + 副标题（支持的格式与流程说明）
 * - dropzone：虚线边框、圆角、hover/dragover 高亮，点击或拖拽均可
 * - preview：选中文件后展示类型徽标 + 文件名 + 大小 + 移除按钮
 * - validation messages：行内红色提示
 * - result：成功 / 失败态
 * - footer：取消 / 开始上传（按 phase 切换）
 *
 * 上传流程：
 * 1. 选择/拖入文件 → beforeSelect 校验扩展名/大小/同名 → 暂存到 selectedFile
 * 2. 点击"开始上传" → 调 docStore.upload(kbId, file)
 * 3. 成功：phase=success，emit('uploaded')；失败：phase=error，保留文件
 */
import { computed, ref, watch } from 'vue'
import { Modal, Button, message } from 'ant-design-vue'
import { UploadCloud, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-vue-next'
import { ApiError, NetworkError, formatApiError } from '@/api/client'
import { useDocumentStore } from '@/stores/document'
import { formatFileSize } from '@/utils/format'
import { fileTypeText } from '@/utils/status'
import FileTypeIcon from '@/components/FileTypeIcon.vue'
import type { DocumentUploadResponse } from '@/types/api'

interface Props {
  open: boolean
  kbId: string
  /** 当前知识库已有文件名列表（用于前端同名检测，大小写不敏感） */
  existingNames?: string[]
}
const props = withDefaults(defineProps<Props>(), {
  existingNames: () => [],
})
const emit = defineEmits<{
  (e: 'update:open', open: boolean): void
  (e: 'uploaded'): void
}>()

const docStore = useDocumentStore()

/** 单文件大小上限：50MB（与后端一致） */
const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
/** 允许的扩展名（小写、含点） */
const ACCEPT_EXT = ['.txt', '.md', '.markdown', '.pdf']
/** input accept 属性 */
const INPUT_ACCEPT = '.txt,.md,.markdown,.pdf'

type Phase = 'idle' | 'uploading' | 'success' | 'error'

const phase = ref<Phase>('idle')
const selectedFile = ref<File | null>(null)
const errorMsg = ref<string>('')
/** 行内校验提示（选择文件阶段，未发请求） */
const validationMsg = ref<string>('')
const result = ref<DocumentUploadResponse | null>(null)
/** 拖拽进入态：用于高亮 dropzone */
const dragActive = ref<boolean>(false)
/** 隐藏 input 的引用 */
const fileInputRef = ref<HTMLInputElement | null>(null)

const isUploading = computed(() => phase.value === 'uploading')
/** 是否可点击"开始上传"：已选文件 + 无行内校验错误 + 未在上传 */
const canSubmit = computed(
  () =>
    phase.value === 'idle' &&
    !!selectedFile.value &&
    !validationMsg.value &&
    !isUploading.value,
)

/** 弹窗打开时重置全部状态 */
watch(
  () => props.open,
  (open) => {
    if (open) {
      phase.value = 'idle'
      selectedFile.value = null
      errorMsg.value = ''
      validationMsg.value = ''
      result.value = null
      dragActive.value = false
    }
  },
)

/** 取文件扩展名（小写，含点） */
function getExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

/** 取文件类型 key（用于 FileTypeIcon） */
function getFileTypeKey(name: string): string {
  const ext = getExt(name).slice(1)
  return ext
}

/**
 * 选择文件前的统一校验入口（点击 / 拖拽均走这里）。
 * 校验顺序：扩展名 → 大小 → 同名。
 * 任何一步失败：写 validationMsg，不暂存文件，不发请求。
 */
function validateAndSelect(file: File): void {
  validationMsg.value = ''
  // 1. 扩展名校验
  const ext = getExt(file.name)
  if (!ACCEPT_EXT.includes(ext)) {
    selectedFile.value = null
    validationMsg.value = `不支持的文件类型：${ext || '未知'}，当前仅支持 TXT、Markdown 和 PDF 文档`
    return
  }
  // 2. 大小校验
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    selectedFile.value = null
    validationMsg.value = `文件大小 ${formatFileSize(file.size)} 超出限制，单个文件不能超过 50MB`
    return
  }
  // 3. 同名校验（基于 existingNames，大小写不敏感、trim 后比较）
  const trimmedName = file.name.trim().toLowerCase()
  const exists = (props.existingNames ?? []).some(
    (n) => (n ?? '').trim().toLowerCase() === trimmedName,
  )
  if (exists) {
    selectedFile.value = null
    validationMsg.value = '当前知识库中已存在同名文件，请重命名后再上传'
    return
  }
  // 4. 通过校验：暂存文件，清空错误
  selectedFile.value = file
  errorMsg.value = ''
  result.value = null
  phase.value = 'idle'
}

/** 点击 dropzone → 触发隐藏 input 的 click */
function handleDropzoneClick(): void {
  if (isUploading.value) return
  fileInputRef.value?.click()
}

/** input change：取第一个文件 */
function handleInputChange(e: Event): void {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  // 清空 input 的 value，允许重复选择同一文件
  target.value = ''
  if (!file) return
  validateAndSelect(file)
}

/** 拖拽进入 / 经过：阻止默认行为，高亮 dropzone */
function handleDragEnter(e: DragEvent): void {
  e.preventDefault()
  e.stopPropagation()
  if (isUploading.value) return
  dragActive.value = true
}
function handleDragOver(e: DragEvent): void {
  e.preventDefault()
  e.stopPropagation()
  if (isUploading.value) return
  dragActive.value = true
}
/** 拖拽离开：取消高亮 */
function handleDragLeave(e: DragEvent): void {
  e.preventDefault()
  e.stopPropagation()
  // 仅当离开 dropzone 容器时才取消高亮（避免子元素切换抖动）
  const related = e.relatedTarget as Node | null
  const currentTarget = e.currentTarget as HTMLElement
  if (!related || !currentTarget.contains(related)) {
    dragActive.value = false
  }
}
/** 拖拽放下：取第一个文件 */
function handleDrop(e: DragEvent): void {
  e.preventDefault()
  e.stopPropagation()
  dragActive.value = false
  if (isUploading.value) return
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return
  if (files.length > 1) {
    message.warning('当前仅支持单文件上传，已选取第一个文件')
  }
  validateAndSelect(files[0])
}

/** 移除已选文件，回到空 dropzone */
function handleClearFile(): void {
  selectedFile.value = null
  validationMsg.value = ''
  errorMsg.value = ''
  result.value = null
  phase.value = 'idle'
}

/**
 * 后端错误 → 中文文案映射。
 * NetworkError / 400 / 409 / 413 / 415 / 5xx / 其他
 * trace_id 如有则附加。
 */
function mapUploadErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) {
    return '无法连接后端服务，请检查 API 地址或服务状态'
  }
  if (err instanceof ApiError) {
    let text: string
    if (err.httpStatus === 400) {
      text = '上传参数不正确，请检查文件后重试'
    } else if (err.httpStatus === 409) {
      text = '当前知识库中已存在同名文件，请重命名后再上传'
    } else if (err.httpStatus === 413) {
      text = '文件过大，请上传不超过 50MB 的文件'
    } else if (err.httpStatus === 415) {
      text = '当前文件格式不支持'
    } else if (err.httpStatus >= 500) {
      text = '服务器内部错误，请稍后重试'
    } else {
      text = err.message
    }
    const trace = err.traceId ? `，trace_id: ${err.traceId}` : ''
    return `${text}${trace}`
  }
  return formatApiError(err)
}

/** 点击"开始上传" */
async function handleSubmit(): Promise<void> {
  if (!selectedFile.value || isUploading.value) return
  // 提交前再校验一次同名（existingNames 可能在弹窗打开后被其他途径更新）
  const trimmedName = selectedFile.value.name.trim().toLowerCase()
  const exists = (props.existingNames ?? []).some(
    (n) => (n ?? '').trim().toLowerCase() === trimmedName,
  )
  if (exists) {
    validationMsg.value = '当前知识库中已存在同名文件，请重命名后再上传'
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
      message.success('文件已存在，已复用已有文档')
    } else {
      message.success('文档上传成功，正在处理')
    }
    emit('uploaded')
  } catch (err) {
    phase.value = 'error'
    errorMsg.value = mapUploadErrorMessage(err)
  }
}

function handleClose(): void {
  emit('update:open', false)
}

/** 失败后重新选择 */
function handleRetrySelect(): void {
  phase.value = 'idle'
  selectedFile.value = null
  errorMsg.value = ''
  result.value = null
  validationMsg.value = ''
}
</script>

<template>
  <Modal
    :open="open"
    title="上传文档"
    :width="560"
    :mask-closable="false"
    :destroy-on-close="true"
    :footer="null"
    wrap-class-name="kb-modal"
    @cancel="handleClose"
  >
    <!-- 副标题 -->
    <p class="upload-modal__subtitle">
      支持 TXT、Markdown、PDF 文档，上传后将自动解析、分块、向量化并建立索引
    </p>

    <!-- 选择 / 上传中 / 失败重试态：共用 dropzone + preview -->
    <div
      v-if="phase === 'idle' || phase === 'uploading' || phase === 'error'"
      class="upload-modal__body"
    >
      <!-- dropzone：原生拖拽 + 隐藏 input -->
      <div
        class="upload-modal__dropzone"
        :class="{
          'upload-modal__dropzone--active': dragActive,
          'upload-modal__dropzone--disabled': isUploading,
        }"
        role="button"
        tabindex="0"
        @click="handleDropzoneClick"
        @keydown.enter.prevent="handleDropzoneClick"
        @keydown.space.prevent="handleDropzoneClick"
        @dragenter="handleDragEnter"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
      >
        <input
          ref="fileInputRef"
          type="file"
          class="upload-modal__input"
          :accept="INPUT_ACCEPT"
          @change="handleInputChange"
        />
        <!-- 上传中：Loader 旋转 + 文案 -->
        <div v-if="isUploading" class="upload-modal__uploading">
          <Loader2 :size="36" class="upload-modal__uploading-icon" />
          <p class="upload-modal__uploading-text">正在上传…</p>
          <p class="upload-modal__uploading-hint">请勿关闭弹窗</p>
        </div>
        <!-- 空态：上传图标 + 主/辅文案 -->
        <template v-else>
          <UploadCloud :size="36" class="upload-modal__dropzone-icon" />
          <p class="upload-modal__dropzone-title">点击或拖拽文件到此处上传</p>
          <p class="upload-modal__dropzone-hint">
            支持 .txt、.md、.markdown、.pdf，单文件最大 50MB
          </p>
        </template>
      </div>

      <!-- 行内校验提示（选择阶段） -->
      <div v-if="validationMsg" class="upload-modal__validation">
        <AlertCircle :size="14" />
        <span>{{ validationMsg }}</span>
      </div>

      <!-- 已选文件预览 -->
      <div v-if="selectedFile && !isUploading" class="upload-modal__preview">
        <FileTypeIcon :file-type="getFileTypeKey(selectedFile.name)" :size="36" />
        <div class="upload-modal__preview-info">
          <span class="upload-modal__preview-name" :title="selectedFile.name">
            {{ selectedFile.name }}
          </span>
          <span class="upload-modal__preview-meta">
            {{ fileTypeText(getFileTypeKey(selectedFile.name)) }} ·
            {{ formatFileSize(selectedFile.size) }}
          </span>
        </div>
        <button
          type="button"
          class="upload-modal__preview-clear"
          :disabled="isUploading"
          title="移除"
          @click="handleClearFile"
        >
          <X :size="14" />
        </button>
      </div>

      <!-- 失败态错误信息（保留已选文件 + 错误提示） -->
      <div v-if="phase === 'error' && errorMsg" class="upload-modal__error">
        <AlertCircle :size="14" />
        <span>{{ errorMsg }}</span>
      </div>
    </div>

    <!-- 上传成功态：成功图标 + 文档编号 -->
    <div v-else-if="phase === 'success' && result" class="upload-modal__result">
      <CheckCircle2 :size="40" class="upload-modal__success-icon" />
      <p class="upload-modal__success-title">文档上传成功，正在处理</p>
      <div class="upload-modal__doc-id">
        <span class="upload-modal__doc-id-label">文档编号：</span>
        <span class="upload-modal__doc-id-value">{{ result.document_id }}</span>
      </div>
      <p v-if="result.duplicated" class="upload-modal__dup">
        该文件已存在，已复用已有文档，无需重复上传。
      </p>
      <p class="upload-modal__tip">
        文档将在后台进行解析、分块、向量化与入库，可在列表中查看状态变化。
      </p>
    </div>

    <!-- 底部按钮 -->
    <div class="upload-modal__footer">
      <template v-if="phase === 'success'">
        <Button type="primary" @click="handleClose">关闭</Button>
      </template>
      <template v-else>
        <Button :disabled="isUploading" @click="handleClose">
          {{ isUploading ? '上传中…' : '取消' }}
        </Button>
        <template v-if="phase === 'error'">
          <Button @click="handleRetrySelect">重新选择</Button>
        </template>
        <Button
          type="primary"
          :loading="isUploading"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          {{ isUploading ? '上传中…' : '开始上传' }}
        </Button>
      </template>
    </div>
  </Modal>
</template>

<style scoped>
.upload-modal__subtitle {
  margin: 4px 0 12px;
  font-size: 13px;
  color: var(--yuxi-gray-600);
  line-height: 1.5;
}

.upload-modal__body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ===== dropzone（虚线边框 + 圆角 + hover/dragover 高亮） ===== */
.upload-modal__dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 16px;
  border: 1.5px dashed var(--yuxi-gray-300);
  border-radius: var(--yuxi-radius);
  background-color: var(--yuxi-gray-25);
  color: var(--yuxi-gray-600);
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
  outline: none;
}

.upload-modal__dropzone:hover {
  border-color: var(--yuxi-main-300);
  background-color: var(--yuxi-main-30);
  color: var(--yuxi-main-color);
}

.upload-modal__dropzone--active {
  border-color: var(--yuxi-main-color);
  background-color: var(--yuxi-main-50);
  color: var(--yuxi-main-color);
  box-shadow: 0 0 0 3px var(--yuxi-main-50);
}

.upload-modal__dropzone--disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.upload-modal__dropzone--disabled:hover {
  border-color: var(--yuxi-gray-300);
  background-color: var(--yuxi-gray-25);
  color: var(--yuxi-gray-600);
}

.upload-modal__input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.upload-modal__dropzone-icon {
  color: var(--yuxi-main-color);
  flex-shrink: 0;
}

.upload-modal__dropzone-title {
  margin: 4px 0 0;
  font-size: 15px;
  font-weight: 500;
  color: var(--yuxi-gray-900);
}

.upload-modal__dropzone-hint {
  margin: 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

/* 上传中态 */
.upload-modal__uploading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
}

.upload-modal__uploading-icon {
  color: var(--yuxi-main-color);
  animation: upload-modal-spin 0.9s linear infinite;
}

.upload-modal__uploading-text {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--yuxi-gray-900);
}

.upload-modal__uploading-hint {
  margin: 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

@keyframes upload-modal-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ===== 行内校验提示 ===== */
.upload-modal__validation {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  border-radius: var(--yuxi-radius-sm);
  background-color: var(--yuxi-error-50);
  border: 1px solid var(--yuxi-error-50);
  color: var(--yuxi-error-700);
  font-size: 12px;
  line-height: 1.5;
}

.upload-modal__validation svg {
  flex-shrink: 0;
  margin-top: 1px;
}

/* ===== 已选文件预览 ===== */
.upload-modal__preview {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background-color: var(--yuxi-gray-25);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
}

.upload-modal__preview-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.upload-modal__preview-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--yuxi-gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-modal__preview-meta {
  font-size: 12px;
  color: var(--yuxi-gray-500);
}

.upload-modal__preview-clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--yuxi-radius-sm);
  background: transparent;
  color: var(--yuxi-gray-500);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  flex-shrink: 0;
}

.upload-modal__preview-clear:hover:not(:disabled) {
  background-color: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
}

.upload-modal__preview-clear:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 失败态错误信息 ===== */
.upload-modal__error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  border-radius: var(--yuxi-radius-sm);
  background-color: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
  font-size: 12px;
  line-height: 1.5;
}

.upload-modal__error svg {
  flex-shrink: 0;
  margin-top: 1px;
}

/* ===== 成功态 ===== */
.upload-modal__result {
  padding: 16px 0 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-modal__success-icon {
  color: var(--yuxi-success-500);
}

.upload-modal__success-title {
  margin: 4px 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--yuxi-gray-900);
}

.upload-modal__doc-id {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  background-color: var(--yuxi-gray-25);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius-sm);
  font-size: 13px;
}

.upload-modal__doc-id-label {
  color: var(--yuxi-gray-500);
}

.upload-modal__doc-id-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--yuxi-gray-700);
}

.upload-modal__dup {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--yuxi-warning-700);
}

.upload-modal__tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--yuxi-gray-500);
  text-align: center;
}

/* ===== 底部按钮 ===== */
.upload-modal__footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* ===== 移动端 ===== */
@media (max-width: 767px) {
  .upload-modal__dropzone {
    padding: 24px 12px;
  }
  .upload-modal__dropzone-title {
    font-size: 14px;
  }
  .upload-modal__dropzone-hint {
    font-size: 11px;
  }
}
</style>
