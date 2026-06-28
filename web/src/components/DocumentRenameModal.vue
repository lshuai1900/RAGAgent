<script setup lang="ts">
/**
 * 文件重命名弹窗
 * - 字段：filename（默认填入当前文件名）
 * - 校验：非空（trim 后），长度 1-256
 * - 保存：显示 loading，避免重复提交
 * - 成功：关闭弹窗，emit renamed（由父组件刷新文件列表）
 * - 失败：显示后端错误信息（同名文件提示"当前知识库中已存在同名文件"）
 */
import { reactive, ref, watch } from 'vue'
import { Modal, Form, FormItem, Input, Button, message } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'
import { useDocumentStore } from '@/stores/document'
import { ApiError, NetworkError } from '@/api/client'
import type { DocumentOut } from '@/types/api'

interface Props {
  open: boolean
  /** 知识库 ID */
  kbId: string
  /** 待重命名的文档（弹窗打开时回填文件名） */
  document: DocumentOut | null
}
const props = defineProps<Props>()

interface Emits {
  (e: 'update:open', open: boolean): void
  (e: 'renamed', doc: DocumentOut): void
}
const emit = defineEmits<Emits>()

const docStore = useDocumentStore()

interface FormState {
  filename: string
}

const formState = reactive<FormState>({ filename: '' })
const formRef = ref()
const submitting = ref<boolean>(false)

/** 文件名校验规则 */
const rules: Record<string, Rule[]> = {
  filename: [
    { required: true, message: '文件名不能为空', trigger: 'blur' },
    { min: 1, max: 256, message: '文件名长度需在 1-256 个字符之间', trigger: 'blur' },
  ],
}

/** 弹窗打开时回填当前文件名 */
watch(
  () => props.open,
  (open) => {
    if (open) {
      formState.filename = props.document?.name ?? ''
      formRef.value?.clearValidate?.()
    }
  },
)

function close(): void {
  emit('update:open', false)
}

/** 后端错误码到中文文案映射 */
function mapRenameErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) return err.message
  if (err instanceof ApiError) {
    // 同一知识库内文档重名
    if (err.code === 10301) return '当前知识库中已存在同名文件'
    // 文档不存在
    if (err.code === 10304) return '文件不存在或已被删除'
    // 知识库不存在
    if (err.code === 10404) return '知识库不存在或已被删除'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return '保存失败，请稍后重试'
}

/** 保存：前端先校验文件名非空（trim），再发 PATCH */
async function handleSubmit(): Promise<void> {
  // 前端 trim + 非空拦截，不发请求
  const trimmedName = formState.filename.trim()
  if (!trimmedName) {
    message.warning('文件名不能为空')
    return
  }

  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  const kbId = props.kbId
  const documentId = props.document?.id
  if (!kbId || !documentId) {
    message.error('文件信息缺失，无法保存')
    return
  }

  // 文件名未变化，直接关闭
  if (trimmedName === props.document?.name) {
    message.info('文件名未变化')
    close()
    return
  }

  submitting.value = true
  try {
    const doc = await docStore.renameDocument(kbId, documentId, {
      filename: trimmedName,
    })
    message.success('文件已重命名')
    emit('renamed', doc)
    close()
  } catch (err) {
    message.error(mapRenameErrorMessage(err))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Modal
    :open="open"
    title="重命名文件"
    :width="480"
    :mask-closable="false"
    :destroy-on-close="true"
    wrap-class-name="kb-modal"
    @cancel="close"
  >
    <Form
      ref="formRef"
      :model="formState"
      :rules="rules"
      layout="vertical"
      class="doc-rename-form"
    >
      <FormItem label="文件名" name="filename">
        <Input
          v-model:value="formState.filename"
          placeholder="请输入新的文件名"
          :maxlength="256"
          allow-clear
          @press-enter="handleSubmit"
        />
      </FormItem>
      <div class="doc-rename-form__tip">
        文件名在同一知识库内必须唯一。修改后不影响已入库的向量索引与分块内容。
      </div>
    </Form>
    <template #footer>
      <Button @click="close">取消</Button>
      <Button type="primary" :loading="submitting" @click="handleSubmit">
        保存
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.doc-rename-form {
  margin-top: 8px;
}

.doc-rename-form__tip {
  margin-top: -8px;
  padding: 8px 12px;
  background-color: #fafafa;
  border: 1px solid var(--app-border);
  border-radius: 4px;
  font-size: 12px;
  color: var(--app-text-tertiary);
  line-height: 1.6;
}
</style>
