<script setup lang="ts">
/**
 * 上传文档弹窗（P1.6 / Yuxi 风格）
 *
 * - 两步交互：选择文件（拖拽/点击）→ 点击"上传"触发上传
 * - 仅允许 .txt / .md / .markdown / .pdf，≤50MB
 * - 上传通过 api/documents.ts 封装（FormData 携带 kb_id），不在组件内写 fetch
 * - 上传成功展示"上传成功，正在后台处理" + 文档编号
 * - 主按钮颜色通过 .kb-modal 局部主题覆盖为低饱和蓝绿色
 * - 未改上传 API、未改状态轮询逻辑
 */
import { computed, ref, watch } from 'vue'
import { Modal, UploadDragger, Button, message, Spin } from 'ant-design-vue'
import type { UploadProps } from 'ant-design-vue'
import { UploadCloud, CheckCircle2, AlertCircle, FileText } from 'lucide-vue-next'
import { ApiError, NetworkError, formatApiError } from '@/api/client'
import { useDocumentStore } from '@/stores/document'
import { formatFileSize } from '@/utils/format'
import { fileTypeText } from '@/utils/status'
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
/** 允许的扩展名 */
const ACCEPT_EXT = ['.txt', '.md', '.markdown', '.pdf']

type Phase = 'idle' | 'uploading' | 'success' | 'error'

const phase = ref<Phase>('idle')
const selectedFile = ref<File | null>(null)
const errorMsg = ref<string>('')
const result = ref<DocumentUploadResponse | null>(null)

const isUploading = computed(() => phase.value === 'uploading')
/** 是否可点击"上传"：已选择合法文件且未在上传 */
const canUpload = computed(
  () => phase.value === 'idle' && !!selectedFile.value && !isUploading.value,
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
    }
  },
)

/** 取文件扩展名（小写，含点） */
function getExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx).toLowerCase() : ''
}

/** beforeUpload：拦截选择，做类型与大小校验，阻止 Antd 自动上传 */
const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  const ext = getExt(file.name)
  if (!ACCEPT_EXT.includes(ext)) {
    message.error(`不支持的文件类型：${ext || '未知'}，仅支持 TXT、Markdown、PDF`)
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    message.error(`文件大小超过限制：${formatFileSize(file.size)}，上限 50MB`)
    return false
  }
  // 仅暂存文件，等待用户点击"上传"
  selectedFile.value = file
  phase.value = 'idle'
  errorMsg.value = ''
  result.value = null
  return false
}

async function handleUpload(): Promise<void> {
  if (!selectedFile.value || isUploading.value) return
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
      message.success('上传成功，正在后台处理')
    }
    emit('uploaded')
  } catch (err) {
    phase.value = 'error'
    if (err instanceof NetworkError) {
      errorMsg.value = err.message
    } else if (err instanceof ApiError) {
      const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
      errorMsg.value = `${err.message}${trace}`
    } else {
      errorMsg.value = formatApiError(err)
    }
  }
}

function handleClose(): void {
  emit('update:open', false)
}

function handleReSelect(): void {
  phase.value = 'idle'
  selectedFile.value = null
  errorMsg.value = ''
  result.value = null
}
</script>

<template>
  <Modal
    :open="open"
    title="上传文档"
    :width="520"
    :mask-closable="false"
    :destroy-on-close="true"
    :footer="null"
    wrap-class-name="kb-modal"
    @cancel="handleClose"
  >
    <!-- 选择 / 上传中 -->
    <div v-if="phase === 'idle' || phase === 'uploading'" class="upload-modal__body">
      <UploadDragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        :multiple="false"
        :disabled="isUploading"
        accept=".txt,.md,.markdown,.pdf"
      >
        <div class="upload-modal__dragger">
          <Spin v-if="isUploading" tip="正在上传…" class="upload-modal__spin" />
          <template v-else>
            <UploadCloud :size="40" class="upload-modal__icon" />
            <p class="upload-modal__title">点击或将文件拖拽到此处</p>
            <p class="upload-modal__hint">支持 TXT、Markdown、PDF 文件</p>
          </template>
        </div>
      </UploadDragger>

      <!-- 已选择文件预览 -->
      <div v-if="selectedFile && !isUploading" class="upload-modal__selected">
        <FileText :size="16" class="upload-modal__selected-icon" />
        <div class="upload-modal__selected-info">
          <span class="upload-modal__selected-name" :title="selectedFile.name">
            {{ selectedFile.name }}
          </span>
          <span class="upload-modal__selected-meta">
            {{ fileTypeText(selectedFile.name.split('.').pop() ?? '') }} ·
            {{ formatFileSize(selectedFile.size) }}
          </span>
        </div>
        <Button type="text" size="small" class="upload-modal__clear" @click="handleReSelect">
          移除
        </Button>
      </div>
    </div>

    <!-- 上传成功 -->
    <div v-else-if="phase === 'success' && result" class="upload-modal__result">
      <CheckCircle2 :size="40" class="upload-modal__success-icon" />
      <p class="upload-modal__success-title">上传成功，正在后台处理</p>
      <div class="upload-modal__doc-id">
        <span class="upload-modal__doc-id-label">文档编号：</span>
        <span class="upload-modal__doc-id-value">{{ result.document_id }}</span>
      </div>
      <p v-if="result.duplicated" class="upload-modal__dup">该文件已存在，已复用已有文档，无需重复上传。</p>
      <p class="upload-modal__tip">文档将在后台进行解析、分块、向量化与入库，可在列表中查看状态变化。</p>
    </div>

    <!-- 上传失败 -->
    <div v-else-if="phase === 'error'" class="upload-modal__result">
      <AlertCircle :size="40" class="upload-modal__error-icon" />
      <p class="upload-modal__error-title">上传失败</p>
      <p class="upload-modal__error-msg">{{ errorMsg }}</p>
    </div>

    <!-- 底部按钮 -->
    <div class="upload-modal__footer">
      <template v-if="phase === 'success'">
        <Button type="primary" @click="handleClose">关闭</Button>
      </template>
      <template v-else-if="phase === 'error'">
        <Button @click="handleClose">关闭</Button>
        <Button type="primary" @click="handleReSelect">重新选择</Button>
      </template>
      <template v-else>
        <Button :disabled="isUploading" @click="handleClose">取消</Button>
        <Button
          type="primary"
          :loading="isUploading"
          :disabled="!canUpload"
          @click="handleUpload"
        >
          上传
        </Button>
      </template>
    </div>
  </Modal>
</template>

<style scoped>
.upload-modal__body {
  padding: 4px 0 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-modal__dragger {
  padding: 32px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-modal__icon {
  color: #8c8c8c;
}

.upload-modal__title {
  margin: 4px 0 0;
  font-size: 15px;
  color: var(--kb-text);
}

.upload-modal__hint {
  margin: 0;
  font-size: 13px;
  color: var(--kb-text-tertiary);
}

.upload-modal__spin {
  padding: 20px 0;
}

.upload-modal__selected {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background-color: #f9fafb;
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
}

.upload-modal__selected-icon {
  color: var(--kb-primary);
  flex-shrink: 0;
}

.upload-modal__selected-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.upload-modal__selected-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--kb-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-modal__selected-meta {
  font-size: 12px;
  color: var(--kb-text-tertiary);
}

.upload-modal__clear {
  flex-shrink: 0;
  color: var(--kb-text-tertiary);
}

.upload-modal__result {
  padding: 16px 0 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-modal__success-icon {
  color: var(--kb-status-success, #16a34a);
}

.upload-modal__success-title {
  margin: 4px 0 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--kb-text);
}

.upload-modal__doc-id {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  background-color: #f9fafb;
  border: 1px solid var(--kb-border);
  border-radius: var(--kb-radius);
  font-size: 13px;
}

.upload-modal__doc-id-label {
  color: var(--kb-text-tertiary);
}

.upload-modal__doc-id-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  color: var(--kb-text-secondary);
}

.upload-modal__dup {
  margin: 8px 0 0;
  font-size: 13px;
  color: #d48806;
}

.upload-modal__tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--kb-text-tertiary);
  text-align: center;
}

.upload-modal__error-icon {
  color: var(--kb-status-error, #dc2626);
}

.upload-modal__error-title {
  margin: 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--kb-text);
}

.upload-modal__error-msg {
  margin: 0;
  font-size: 13px;
  color: var(--kb-status-error, #dc2626);
  text-align: center;
  word-break: break-all;
}

.upload-modal__footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
