<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 8：知识库详情页 Chat Tab，嵌入式 RagChatPanel。
-->
<script setup lang="ts">
/**
 * 知识库详情页 - 聊天问答 Tab（Step 8 / Yuxi 风格）
 *
 * - 使用当前 route.params.kbId，不要求用户重新选择知识库
 * - 显示轻量提示：当前知识库：xxx
 * - 复用 RagChatPanel（embedded=true）
 * - 不显示会话历史 / Agent / Tool 入口
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import RagChatPanel from '@/components/chat/RagChatPanel.vue'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId ?? ''))

const kbStore = useKnowledgeBaseStore()
const { detail } = storeToRefs(kbStore)

const kbName = computed(() => detail.value?.name ?? '')
</script>

<template>
  <div class="kb-chat-tab">
    <!-- 轻量知识库提示 -->
    <div v-if="kbName" class="kb-chat-tab__hint">
      当前知识库：{{ kbName }}
    </div>

    <!-- 聊天面板（嵌入式，不显示大标题） -->
    <RagChatPanel
      :kb-id="kbId"
      :embedded="true"
    />
  </div>
</template>

<style scoped>
.kb-chat-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.kb-chat-tab__hint {
  flex-shrink: 0;
  padding: 8px 14px;
  margin-bottom: 12px;
  background: var(--yuxi-main-30);
  border: 1px solid var(--yuxi-main-100);
  border-radius: var(--yuxi-radius-sm);
  font-size: 13px;
  color: var(--yuxi-main-700);
}
</style>
