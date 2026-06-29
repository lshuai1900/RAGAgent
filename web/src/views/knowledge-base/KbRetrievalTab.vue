<script setup lang="ts">
/**
 * 知识库详情页 - 检索测试 Tab（子路由视图）
 *
 * 复用 SearchTestPanel（mode=search, layout=horizontal）。
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBase'
import SearchTestPanel from '@/components/SearchTestPanel.vue'

const route = useRoute()
const kbId = computed(() => String(route.params.kbId ?? ''))

const kbStore = useKnowledgeBaseStore()
const { detail } = storeToRefs(kbStore)
</script>

<template>
  <SearchTestPanel :kb-id="kbId" :kb-name="detail?.name" />
</template>
