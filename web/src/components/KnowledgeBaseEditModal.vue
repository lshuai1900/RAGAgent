<script setup lang="ts">
/**
 * 编辑知识库弹窗
 * - 修改名称（trim，非空校验）
 * - 修改描述
 * - 危险操作区：删除知识库（二次确认）
 *
 * 复用 store 的 updateKb / deleteKb，保存成功后由父组件刷新详情，
 * 删除成功后由父组件跳转回列表页。
 */
import { reactive, ref, watch } from 'vue'
import { Modal, Form, FormItem, Input, Textarea, Button, Select, message } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { ApiError, NetworkError } from '@/api/client'
import type { KnowledgeBaseOut } from '@/types/api'

interface Props {
  open: boolean
  /** 当前知识库详情（用于回填表单） */
  knowledgeBase: KnowledgeBaseOut | null
}
const props = defineProps<Props>()

interface Emits {
  (e: 'update:open', open: boolean): void
  (e: 'updated', kb: KnowledgeBaseOut): void
  (e: 'deleted', kbId: string): void
}
const emit = defineEmits<Emits>()

const kbStore = useKnowledgeBaseStore()

interface FormState {
  name: string
  description: string
  status: 'active' | 'archived'
}

const formState = reactive<FormState>({ name: '', description: '', status: 'active' })
const formRef = ref()
const submitting = ref<boolean>(false)
const deleting = ref<boolean>(false)

/** 状态选项 */
const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'archived', label: '已归档' },
]

/** 名称校验规则 */
const rules: Record<string, Rule[]> = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 128, message: '名称长度需在 1-128 个字符之间', trigger: 'blur' },
  ],
  description: [{ max: 512, message: '描述最长 512 个字符', trigger: 'blur' }],
}

/** 弹窗打开时回填当前知识库名称、描述与状态 */
watch(
  () => props.open,
  (open) => {
    if (open) {
      formState.name = props.knowledgeBase?.name ?? ''
      formState.description = props.knowledgeBase?.description ?? ''
      const currentStatus = props.knowledgeBase?.status
      formState.status = currentStatus === 'archived' ? 'archived' : 'active'
      formRef.value?.clearValidate?.()
    }
  },
)

function close(): void {
  emit('update:open', false)
}

/** 后端错误码到中文文案映射 */
function mapUpdateErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) return err.message
  if (err instanceof ApiError) {
    // 重名错误
    if (err.code === 10101) return '知识库名称已存在'
    // 不存在
    if (err.code === 10404) return '知识库不存在或已被删除'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return '保存失败，请稍后重试'
}

/** 保存：前端先校验名称非空（trim），再发 PATCH */
async function handleSubmit(): Promise<void> {
  // 前端 trim + 非空拦截，不发请求
  const trimmedName = formState.name.trim()
  if (!trimmedName) {
    message.warning('知识库名称不能为空')
    return
  }

  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  const kbId = props.knowledgeBase?.id
  if (!kbId) {
    message.error('知识库信息缺失，无法保存')
    return
  }

  submitting.value = true
  try {
    const kb = await kbStore.updateKb(kbId, {
      name: trimmedName,
      description: formState.description.trim() || null,
      status: formState.status,
    })
    message.success('知识库已更新')
    emit('updated', kb)
    close()
  } catch (err) {
    message.error(mapUpdateErrorMessage(err))
  } finally {
    submitting.value = false
  }
}

/** 删除：二次确认后调用 DELETE */
function handleDelete(): void {
  const kbId = props.knowledgeBase?.id
  const kbName = props.knowledgeBase?.name ?? '该知识库'
  if (!kbId) {
    message.error('知识库信息缺失，无法删除')
    return
  }

  Modal.confirm({
    title: '删除知识库',
    content: `即将删除知识库「${kbName}」。删除后该知识库将无法在列表中继续使用，相关文档和向量索引会按后端逻辑清理。此操作不可撤销，是否继续？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      deleting.value = true
      try {
        await kbStore.deleteKb(kbId)
        message.success('知识库已删除')
        emit('deleted', kbId)
        close()
      } catch (err) {
        message.error(mapDeleteErrorMessage(err))
      } finally {
        deleting.value = false
      }
    },
  })
}

function mapDeleteErrorMessage(err: unknown): string {
  if (err instanceof NetworkError) return err.message
  if (err instanceof ApiError) {
    if (err.code === 10404) return '知识库不存在或已被删除'
    const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
    return `${err.message}${trace}`
  }
  return '删除失败，请稍后重试'
}
</script>

<template>
  <Modal
    :open="open"
    title="编辑知识库"
    :width="560"
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
      class="kb-edit-form"
    >
      <FormItem label="知识库名称" name="name">
        <Input
          v-model:value="formState.name"
          placeholder="请输入知识库名称"
          :maxlength="128"
          allow-clear
        />
      </FormItem>
      <FormItem label="描述" name="description">
        <Textarea
          v-model:value="formState.description"
          placeholder="请输入描述（可选）"
          :maxlength="512"
          :rows="2"
        />
      </FormItem>
      <FormItem label="状态" name="status">
        <Select v-model:value="formState.status" :options="statusOptions" />
      </FormItem>
      <div class="kb-edit-form__tip">
        仅名称、描述与状态可修改；Embedding 模型、向量维度、分块策略创建后不可变更。
      </div>

      <!-- 危险操作区 -->
      <div class="kb-edit-danger">
        <div class="kb-edit-danger__head">危险操作</div>
        <div class="kb-edit-danger__row">
          <div class="kb-edit-danger__text">
            <div class="kb-edit-danger__title">删除知识库</div>
            <div class="kb-edit-danger__desc">
              将知识库归档并尝试清理向量库 collection，删除后不再出现在列表中。
            </div>
          </div>
          <Button danger :loading="deleting" :disabled="submitting" @click="handleDelete">
            删除知识库
          </Button>
        </div>
      </div>
    </Form>
    <template #footer>
      <Button @click="close">取消</Button>
      <Button type="primary" :loading="submitting" :disabled="deleting" @click="handleSubmit">
        保存
      </Button>
    </template>
  </Modal>
</template>

<style scoped>
.kb-edit-form {
  margin-top: 8px;
}

.kb-edit-form__tip {
  margin-top: -8px;
  padding: 8px 12px;
  background-color: #fafafa;
  border: 1px solid var(--app-border);
  border-radius: 4px;
  font-size: 12px;
  color: var(--app-text-tertiary);
  line-height: 1.6;
}

/* 危险操作区 */
.kb-edit-danger {
  margin-top: 20px;
  border: 1px solid var(--kb-error, #ffccc7);
  border-radius: var(--kb-radius, 8px);
  overflow: hidden;
}

.kb-edit-danger__head {
  padding: 8px 12px;
  background-color: var(--kb-error-bg, #fff1f0);
  color: var(--kb-error-strong, #cf1322);
  font-size: 13px;
  font-weight: 600;
}

.kb-edit-danger__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px;
}

.kb-edit-danger__text {
  min-width: 0;
}

.kb-edit-danger__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--kb-text-title, #1e1f1f);
}

.kb-edit-danger__desc {
  margin-top: 2px;
  font-size: 12px;
  color: var(--kb-text-tertiary, #697070);
  line-height: 1.5;
}
</style>
