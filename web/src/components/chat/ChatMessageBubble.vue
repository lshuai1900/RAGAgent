<!--
  Adapted from xerrors/Yuxi under MIT License.
  Original project: `https://github.com/xerrors/Yuxi`
  Version: v0.7.0
  Modified for RAGAgent lightweight RAG-only scope.
  Step 8：Yuxi 风格聊天消息气泡，区分 user/assistant，assistant 支持流式/引用来源。
-->
<script setup lang="ts">
/**
 * 聊天消息气泡（Step 8）
 *
 * - 用户消息：右对齐，main-50 背景
 * - AI 消息：左对齐，gray-50 背景
 * - streaming + 无内容：显示"正在生成回答…"
 * - error：红色错误提示
 * - done：trace_id / finish_reason / 引用来源卡片
 * - 不引入 Markdown 渲染；content 用 pre-wrap
 */
import { computed } from 'vue'
import { Bot, User, Loader, AlertCircle } from 'lucide-vue-next'
import SourceReferenceCard from '@/components/chat/SourceReferenceCard.vue'
import type { ChatMessage } from '@/utils/chatReferences'

interface Props {
  message: ChatMessage
}
const props = defineProps<Props>()

const isUser = computed(() => props.message.role === 'user')
const isStreaming = computed(() => props.message.streaming === true)
const hasReferences = computed(
  () => !isUser.value && (props.message.references?.length ?? 0) > 0,
)
const showThinking = computed(
  () => !isUser.value && isStreaming.value && !props.message.content,
)
</script>

<template>
  <div class="bubble" :class="isUser ? 'bubble--user' : 'bubble--assistant'">
    <!-- 头像 -->
    <div class="bubble__avatar">
      <component :is="isUser ? User : Bot" :size="16" />
    </div>

    <!-- 主体 -->
    <div class="bubble__body">
      <!-- 元信息行 -->
      <div class="bubble__meta">
        <span class="bubble__role">{{ isUser ? '用户' : '助手' }}</span>
        <span v-if="isStreaming" class="bubble__status bubble__status--streaming">
          <Loader :size="11" class="bubble__spin" />
          生成中
        </span>
        <span v-else-if="message.error" class="bubble__status bubble__status--error">
          生成失败
        </span>
      </div>

      <!-- 内容 -->
      <div class="bubble__content">
        <span v-if="showThinking" class="bubble__thinking">正在生成回答…</span>
        <pre v-else class="bubble__pre">{{ message.content }}</pre>
      </div>

      <!-- 错误 -->
      <div v-if="message.error" class="bubble__error">
        <AlertCircle :size="13" />
        <span>{{ message.error }}</span>
      </div>

      <!-- 元数据：trace_id / finish_reason -->
      <div
        v-if="!isUser && !isStreaming && (message.traceId || message.finishReason)"
        class="bubble__meta-data"
      >
        <span v-if="message.traceId" class="bubble__meta-item">
          <span class="bubble__meta-label">追踪编号</span>
          <span class="bubble__meta-value">{{ message.traceId }}</span>
        </span>
        <span v-if="message.finishReason" class="bubble__meta-item">
          <span class="bubble__meta-label">结束原因</span>
          <span class="bubble__meta-value">{{ message.finishReason }}</span>
        </span>
      </div>

      <!-- 引用来源 -->
      <div v-if="hasReferences" class="bubble__sources">
        <div class="bubble__sources-title">引用来源</div>
        <SourceReferenceCard
          v-for="(ref, idx) in message.references"
          :key="idx"
          :reference="ref"
          :index="idx + 1"
        />
      </div>
      <div
        v-else-if="!isUser && !isStreaming && !message.error && message.content"
        class="bubble__no-sources"
      >
        暂无引用来源
      </div>
    </div>
  </div>
</template>

<style scoped>
.bubble {
  display: flex;
  gap: 10px;
  max-width: 100%;
}

/* 用户消息：右对齐 */
.bubble--user {
  flex-direction: row-reverse;
}

.bubble--user .bubble__body {
  align-items: flex-end;
}

.bubble--user .bubble__avatar {
  background: var(--yuxi-main-50);
  color: var(--yuxi-main-700);
}

.bubble--user .bubble__pre {
  background: var(--yuxi-main-50);
  color: var(--yuxi-gray-800);
  border-color: var(--yuxi-main-100);
}

/* AI 消息：左对齐 */
.bubble--assistant .bubble__avatar {
  background: var(--yuxi-gray-100);
  color: var(--yuxi-gray-700);
}

.bubble--assistant .bubble__pre {
  background: var(--yuxi-gray-50);
  color: var(--yuxi-gray-800);
  border-color: var(--yuxi-gray-150);
}

.bubble__avatar {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bubble__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bubble--user .bubble__body {
  max-width: 80%;
}

.bubble--assistant .bubble__body {
  max-width: 85%;
}

.bubble__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.bubble--user .bubble__meta {
  flex-direction: row-reverse;
}

.bubble__role {
  font-weight: 600;
  color: var(--yuxi-gray-600);
}

.bubble__status {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 1px 6px;
  border-radius: var(--yuxi-radius-pill);
  font-size: 11px;
}

.bubble__status--streaming {
  background: var(--yuxi-main-50);
  color: var(--yuxi-main-600);
}

.bubble__status--error {
  background: var(--yuxi-error-50);
  color: var(--yuxi-error-700);
}

.bubble__spin {
  animation: bubble-spin 1s linear infinite;
}

@keyframes bubble-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.bubble__content {
  min-width: 0;
}

.bubble__pre {
  margin: 0;
  padding: 10px 14px;
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.7;
}

.bubble__thinking {
  color: var(--yuxi-gray-500);
  font-style: italic;
  font-size: 14px;
  padding: 10px 14px;
  background: var(--yuxi-gray-50);
  border: 1px solid var(--yuxi-gray-150);
  border-radius: var(--yuxi-radius);
}

.bubble__error {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  border-radius: var(--yuxi-radius-sm);
  background: var(--yuxi-error-50);
  border: 1px solid var(--yuxi-error-500);
  color: var(--yuxi-error-700);
  font-size: 13px;
  line-height: 1.5;
}

.bubble__meta-data {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 4px;
}

.bubble__meta-item {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.bubble__meta-label {
  font-size: 11px;
  color: var(--yuxi-gray-400);
}

.bubble__meta-value {
  font-size: 12px;
  color: var(--yuxi-gray-600);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
}

.bubble__sources {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bubble__sources-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--yuxi-gray-600);
}

.bubble__no-sources {
  margin-top: 6px;
  font-size: 12px;
  color: var(--yuxi-gray-400);
}
</style>
