<script setup lang="ts">
/**
 * 检索测试面板（P1.4-B）
 *
 * - 复用 ChatSsePanel，以 mode='search' + layout='horizontal' 适配检索测试场景
 * - 调用 POST /api/v1/chat/sse，复用已有 fetch + ReadableStream SSE 解析
 * - 不伪造检索结果，不实现独立检索 API
 * - 后端无 retrieval_context 时显示"暂无引用来源"
 */
import ChatSsePanel from '@/components/ChatSsePanel.vue'

interface Props {
  /** 当前知识库 ID */
  kbId: string
  /** 当前知识库名称 */
  kbName?: string
}
const props = defineProps<Props>()
</script>

<template>
  <ChatSsePanel
    :kb-id="props.kbId"
    :kb-name="props.kbName"
    mode="search"
    layout="horizontal"
  />
</template>
