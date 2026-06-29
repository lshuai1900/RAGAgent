<script setup lang="ts">
/**
 * 知识库详情页 - 聊天问答 Tab（子路由视图）
 *
 * 复用 ChatSsePanel（mode=chat, layout=vertical）。
 * 聊天问答与检索测试共用同一 SSE 接口，仅交互形态不同。
 */
import { computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import { useChatStore } from '@/stores/chat'
import ChatSsePanel from '@/components/ChatSsePanel.vue'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId ?? ''))

const kbStore = useKnowledgeBaseStore()
const chatStore = useChatStore()
const { detail } = storeToRefs(kbStore)

// 离开聊天 Tab 时重置聊天状态，避免与检索测试串状态
onBeforeUnmount(() => {
  chatStore.reset()
})
</script>

<template>
  <ChatSsePanel :kb-id="kbId" :kb-name="detail?.name" mode="chat" layout="vertical" />
</template>
