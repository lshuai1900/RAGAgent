<script setup lang="ts">
/**
 * 新建知识库弹窗
 * - Embedding 模型与向量维度默认只读展示（避免与后端不一致）
 * - 分块策略默认 recursive（MVP 不暴露切换，避免误填）
 */
import { reactive, ref, watch } from 'vue'
import { Modal, Form, FormItem, Input, Textarea, InputNumber, Button, message } from 'ant-design-vue'
import type { Rule } from 'ant-design-vue/es/form'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { ApiError, NetworkError } from '@/api/client'
import type { KnowledgeBaseCreate } from '@/types/api'

interface Props {
  open: boolean
}
const props = defineProps<Props>()

interface Emits {
  (e: 'update:open', open: boolean): void
  (e: 'created'): void
}
const emit = defineEmits<Emits>()

const kbStore = useKnowledgeBaseStore()

interface FormState {
  name: string
  description: string
  embeddingModel: string
  embeddingDim: number
  chunkSize: number
  chunkOverlap: number
}

const DEFAULT_FORM: FormState = {
  name: '',
  description: '',
  embeddingModel: 'text-embedding-v3',
  embeddingDim: 1024,
  chunkSize: 512,
  chunkOverlap: 64,
}

const formState = reactive<FormState>({ ...DEFAULT_FORM })
const formRef = ref()
const submitting = ref<boolean>(false)

/** 校验规则 */
const rules: Record<string, Rule[]> = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 128, message: '名称长度需在 1-128 个字符之间', trigger: 'blur' },
  ],
  description: [{ max: 512, message: '描述最长 512 个字符', trigger: 'blur' }],
  embeddingDim: [
    { required: true, message: '请输入向量维度', trigger: 'blur' },
    {
      validator: (_rule: Rule, value: number) =>
        value > 0 && value <= 8192 ? Promise.resolve() : Promise.reject(new Error('向量维度需在 1-8192 之间')),
      trigger: 'blur',
    },
  ],
  chunkSize: [
    { required: true, message: '请输入分块大小', trigger: 'blur' },
    {
      validator: (_rule: Rule, value: number) =>
        value > 0 && value <= 8192 ? Promise.resolve() : Promise.reject(new Error('分块大小需在 1-8192 之间')),
      trigger: 'blur',
    },
  ],
  chunkOverlap: [
    { required: true, message: '请输入分块重叠', trigger: 'blur' },
    {
      validator: (_rule: Rule, value: number) => {
        if (value < 0 || value >= 8192) {
          return Promise.reject(new Error('分块重叠需在 0-8191 之间'))
        }
        if (value >= formState.chunkSize) {
          return Promise.reject(new Error('分块重叠必须小于分块大小'))
        }
        return Promise.resolve()
      },
      trigger: 'blur',
    },
  ],
}

/** 弹窗打开时重置表单 */
watch(
  () => props.open,
  (open) => {
    if (open) {
      Object.assign(formState, DEFAULT_FORM)
      formRef.value?.clearValidate?.()
    }
  },
)

function close(): void {
  emit('update:open', false)
}

async function handleSubmit(): Promise<void> {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  submitting.value = true
  const payload: KnowledgeBaseCreate = {
    name: formState.name.trim(),
    description: formState.description.trim() || undefined,
    embedding_model: formState.embeddingModel,
    embedding_dim: formState.embeddingDim,
    chunk_strategy: 'recursive',
    chunk_size: formState.chunkSize,
    chunk_overlap: formState.chunkOverlap,
  }
  try {
    await kbStore.createKb(payload)
    message.success('创建成功')
    emit('created')
    close()
  } catch (err) {
    if (err instanceof NetworkError) {
      message.error(err.message)
    } else if (err instanceof ApiError) {
      const trace = err.traceId ? `，追踪编号：${err.traceId}` : ''
      message.error(`${err.message}${trace}`)
    } else {
      message.error('创建失败，请稍后重试')
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Modal
    :open="open"
    title="新建知识库"
    :width="560"
    :mask-closable="false"
    :destroy-on-close="true"
    @cancel="close"
  >
    <Form
      ref="formRef"
      :model="formState"
      :rules="rules"
      layout="vertical"
      class="kb-create-form"
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
      <div class="kb-create-form__row">
        <FormItem label="Embedding 模型" name="embeddingModel" class="kb-create-form__col">
          <Input v-model:value="formState.embeddingModel" disabled />
        </FormItem>
        <FormItem label="向量维度" name="embeddingDim" class="kb-create-form__col">
          <InputNumber
            v-model:value="formState.embeddingDim"
            :min="1"
            :max="8192"
            style="width: 100%"
          />
        </FormItem>
      </div>
      <div class="kb-create-form__row">
        <FormItem label="分块大小" name="chunkSize" class="kb-create-form__col">
          <InputNumber
            v-model:value="formState.chunkSize"
            :min="1"
            :max="8192"
            style="width: 100%"
          />
        </FormItem>
        <FormItem label="分块重叠" name="chunkOverlap" class="kb-create-form__col">
          <InputNumber
            v-model:value="formState.chunkOverlap"
            :min="0"
            :max="8191"
            style="width: 100%"
          />
        </FormItem>
      </div>
      <div class="kb-create-form__tip">
        分块策略默认使用 recursive；Embedding 模型与维度默认与后端配置一致，请勿随意修改。
      </div>
    </Form>
    <template #footer>
      <Button @click="close">取消</Button>
      <Button type="primary" :loading="submitting" @click="handleSubmit">创建知识库</Button>
    </template>
  </Modal>
</template>

<style scoped>
.kb-create-form {
  margin-top: 8px;
}

.kb-create-form__row {
  display: flex;
  gap: 16px;
}

.kb-create-form__col {
  flex: 1;
}

.kb-create-form__tip {
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
