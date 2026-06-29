/**
 * 路由表：
 * - / 仪表盘（Yuxi 风格，调 GET /health）
 * - /dashboard 兼容旧入口，重定向到 /
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '仪表盘' },
  },
  { path: '/dashboard', redirect: '/' },
  {
    path: '/knowledge-bases',
    name: 'knowledgeBaseList',
    component: () => import('@/views/KnowledgeBaseListView.vue'),
    meta: { title: '知识库' },
  },
  {
    path: '/knowledge-bases/:kbId',
    component: () => import('@/views/KnowledgeBaseDetailView.vue'),
    // immersive: 详情页使用沉浸式布局（隐藏全局侧栏）
    meta: { title: '知识库详情', immersive: true },
    props: true,
    children: [
      { path: '', redirect: (to) => `/knowledge-bases/${to.params.kbId}/files` },
      {
        path: 'files',
        name: 'knowledgeBaseFiles',
        component: () => import('@/views/knowledge-base/KbFilesTab.vue'),
        meta: { title: '文件管理', tab: 'files' },
      },
      {
        path: 'retrieval',
        name: 'knowledgeBaseRetrieval',
        component: () => import('@/views/knowledge-base/KbRetrievalTab.vue'),
        meta: { title: '检索测试', tab: 'retrieval' },
      },
      {
        path: 'chat',
        name: 'knowledgeBaseChat',
        component: () => import('@/views/knowledge-base/KbChatTab.vue'),
        meta: { title: '聊天问答', tab: 'chat' },
      },
    ],
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '聊天问答' },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: '设置' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'notFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面未找到' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  const title = (to.meta.title as string | undefined) ?? 'RAGAgent 控制台'
  document.title = `${title} · RAGAgent 控制台`
})

export default router
