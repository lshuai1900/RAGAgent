/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

// 路由元信息类型扩展（P1.6：immersive 用于知识库详情页沉浸式布局）
// 注意：必须先 import 'vue-router'，使本声明变为模块增强而非模块替换
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    immersive?: boolean
  }
}

