/**
 * 路由表：/ 重定向到 /knowledge-bases
 * P1.1 阶段所有页面均为占位或基础实现，不接业务 API（仅 /dashboard 调 /health）
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/knowledge-bases' },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: '仪表盘' },
  },
  {
    path: '/knowledge-bases',
    name: 'knowledgeBaseList',
    component: () => import('@/views/KnowledgeBaseListView.vue'),
    meta: { title: '知识库' },
  },
  {
    path: '/knowledge-bases/:kbId',
    name: 'knowledgeBaseDetail',
    component: () => import('@/views/KnowledgeBaseDetailView.vue'),
    meta: { title: '知识库详情' },
    props: true,
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
