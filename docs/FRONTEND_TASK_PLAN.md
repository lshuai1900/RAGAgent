# FRONTEND_TASK_PLAN.md

> Ragent-Py 前端任务拆分与批次推进计划（P1.0 - P1.5）
>
> 严格分批推进：每批完成后必须通过 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` 对应批次验收，才能启动下一批。
> 禁止一次性实现所有页面，禁止跨批次提交。

---

## 总览

| 批次 | 范围 | 产出 |
|---|---|---|
| P1.0 | 前端设计与规则落地（本轮） | 文档 + 规则，零业务代码 |
| P1.1 | Vue 项目骨架 + 布局 + 中文菜单 | 可启动的空壳工程 |
| P1.2 | 知识库列表页 + 新建知识库 | 列表卡片 + 新建弹窗 |
| P1.3 | 知识库详情页 + 文件管理 + 上传文档 | 详情标签页 + 文档表格 + 上传 + 轮询 |
| P1.4 | 聊天问答 + POST SSE 流式输出 | SSE 流式问答页 |
| P1.5 | 联调、中文 UI 验收、README 更新 | 端到端可用 + 文档闭环 |

**推进纪律**：
- 每批开始前确认当前批次编号
- 每批完成后输出新增文件清单 + 验收结果，等待用户确认
- 范围拦截：用户要求实现超出当前批次的功能时，主动拒绝并提示当前批次范围
- 暂缓项拦截：用户要求实现暂缓项（见 `web/AGENTS.md`）时，立即停止并说明

---

## P1.0　前端设计与规则落地（本轮）

### 目标
为前端工程制定设计文档、架构文档、API 契约、任务拆分、验收标准与 Trae 规则，确保后续 P1.1-P1.5 有据可依。

### 允许实现内容（仅文档与规则）
- `docs/FRONTEND_UI_SPEC.md`：UI 设计规范
- `docs/FRONTEND_ARCHITECTURE.md`：前端架构与目录结构
- `docs/FRONTEND_API_CONTRACT.md`：前后端 API 契约
- `docs/FRONTEND_TASK_PLAN.md`：任务拆分（本文件）
- `docs/FRONTEND_ACCEPTANCE_CRITERIA.md`：每批验收标准
- `web/AGENTS.md`：前端 AI 协作规则
- `.trae/rules/frontend-ui.mdc`
- `.trae/rules/vue-conventions.mdc`
- `.trae/rules/ant-design-vue.mdc`
- `.trae/rules/frontend-task-batch.mdc`
- `.trae/rules/frontend-api-client.mdc`
- `.trae/rules/frontend-sse.mdc`

### 禁止实现内容
- ❌ 任何 Vue / TypeScript 业务代码
- ❌ `web/` 下的 `package.json` / `vite.config.ts` / `tsconfig.json` 等工程文件
- ❌ API 请求代码、Pinia store、SSE 解析代码、组件代码
- ❌ 后端任何改动（包括 CORS）
- ❌ 复制 Yuxi 仓库源码

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.0 节。

---

## P1.1　Vue 项目骨架 + 布局 + 中文菜单

### 目标
搭建可启动的 Vue 3 + Vite + TypeScript 空壳工程，包含全局布局、路由表、中文顶部导航，但**不实现任何业务页面**。

### 允许实现内容
- `web/` 工程初始化：`package.json` / `vite.config.ts` / `tsconfig.json` / `index.html` / `env.d.ts`
- 依赖安装：vue / vue-router / pinia / ant-design-vue / lucide-vue-next / dayjs
- `src/main.ts`：挂载 Pinia + Router + Antd（按需引入或全量引入二选一）
- `src/App.vue`：根组件
- `src/router/index.ts`：路由表（4 条路由，见 UI 规范第 5 节）
- `src/layouts/DefaultLayout.vue`：顶部导航 + `<router-view />`
- `src/views/NotFound.vue`：404 页（中文文案）
- `src/stores/settings.ts`：`apiBaseUrl` 的 localStorage 读写（含默认值兜底）
- `src/api/client.ts`：基础 fetch 封装骨架（baseUrl 拼接 + ApiResponse 解析 + 错误处理）
- `src/api/health.ts`：`GET /health` 客户端
- `src/types/api.ts` / `src/types/enums.ts`：类型定义骨架
- `src/utils/format.ts`：状态文案映射、文件大小/时间格式化
- 顶部导航中文菜单：标题"RAGAgent 控制台" + "知识库" + "设置"入口
- 各业务页面占位（`views/knowledge-base/List.vue` 等仅放标题占位，不实现业务）

### 禁止实现内容
- ❌ 知识库卡片组件、新建弹窗
- ❌ 文档表格、上传组件、轮询
- ❌ 聊天组件、SSE 解析
- ❌ 设置页表单交互（仅放占位）
- ❌ Mock 数据 / 假数据
- ❌ 调用知识库/文档/聊天接口（仅 `health.ts` 可用，供设置页测试连接）

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.1 节。

---

## P1.2　知识库列表页 + 新建知识库

### 目标
实现知识库列表页（卡片网格）与新建知识库弹窗，对接 `POST/GET /api/v1/knowledge-bases`。

### 允许实现内容
- `src/api/knowledgeBase.ts`：知识库 CRUD 客户端
- `src/stores/knowledgeBase.ts`：列表状态 + 加载状态
- `src/views/knowledge-base/List.vue`：列表页（卡片网格 + 空状态 + 新建按钮）
- `src/components/knowledge-base/KbCard.vue`：知识库卡片
- `src/components/knowledge-base/CreateKbModal.vue`：新建弹窗（表单 + 校验）
- 列表加载（`onMounted` 调 `GET /api/v1/knowledge-bases`）
- 新建提交（`POST /api/v1/knowledge-bases`，成功后刷新列表）
- 错误提示（中文 + 追踪编号）
- 状态标签中文映射（`utils/format.ts` 复用）
- 点击卡片跳转详情页（路由跳转，详情页可仍为占位）

### 禁止实现内容
- ❌ 知识库详情页业务内容（仅路由可达，页面占位）
- ❌ 文档管理、上传、轮询
- ❌ 聊天问答、SSE
- ❌ 文档删除 / 知识库删除（后端无接口）
- ❌ 知识库编辑（后端 MVP 无 update 路由）

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.2 节。

---

## P1.3　知识库详情页 + 文件管理 + 上传文档

### 目标
实现知识库详情页框架（顶部信息 + 标签页）与文件管理标签页（上传 + 状态统计 + 表格 + 轮询）。

### 允许实现内容
- `src/api/document.ts`：文档上传/列表/查询客户端
- `src/views/knowledge-base/Detail.vue`：详情页框架（顶部信息 + Tabs）
- `src/components/document/UploadModal.vue`：上传弹窗（选文件 + 校验大小 + FormData 上传）
- `src/components/document/DocumentTable.vue`：文档表格（中文列名 + 状态 Tag）
- `src/components/document/StatusTag.vue`：状态标签组件
- `src/composables/usePolling.ts`：轮询封装
- 文件管理标签页：状态统计 + 表格 + 上传按钮 + 轮询
- 标签页切换同步 `route.query.tab`
- 其他标签页（检索测试/聊天问答/配置）放占位，不实现
- 顶部"← 返回"按钮回列表页

### 禁止实现内容
- ❌ 聊天问答、SSE
- ❌ 检索测试（后端无独立检索接口，占位"功能开发中"）
- ❌ 文档删除（后端无接口，删除按钮置灰）
- ❌ 文档重新摄取
- ❌ 知识库配置编辑（配置标签页占位）

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.3 节。

---

## P1.4　聊天问答 + POST SSE 流式输出

### 目标
实现聊天问答标签页，对接 `POST /api/v1/chat/sse`，用 fetch + ReadableStream 解析 SSE。

### 允许实现内容
- `src/api/chat.ts`：SSE 客户端（fetch + ReadableStream + 事件解析）
- `src/composables/useSseChat.ts`：SSE 流式问答封装（响应式状态 + 回调）
- `src/stores/chat.ts`：会话状态（session_id、消息列表）
- `src/components/chat/ChatPanel.vue`：聊天主面板
- `src/components/chat/MessageItem.vue`：单条消息
- `src/components/chat/CitationList.vue`：引用来源列表（占位，因后端暂未下发引用）
- `src/utils/uuid.ts`：session_id 生成（`crypto.randomUUID`）
- 聊天问答标签页：选知识库 + 输入问题 + 流式输出 + 错误处理
- session_id 由前端生成，"新建对话"重置
- loading 文案"正在思考…"
- 错误展示中文 message + 追踪编号
- 引用来源区域占位"本次回答无引用来源"（后端 done 事件暂无 citations）

### 禁止实现内容
- ❌ 使用 `EventSource`（必须 fetch + ReadableStream）
- ❌ 引用来源真实渲染（后端未下发，仅占位）
- ❌ 对话历史持久化查询（后端 MVP 未暴露 list 路由）
- ❌ 对话标题自动生成
- ❌ 多知识库路由

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.4 节。

---

## P1.5　联调、中文 UI 验收、README 更新

### 目标
端到端联调，确保前后端打通；全量中文 UI 验收；更新 README 与部署说明。

### 允许实现内容
- 后端补 `CORSMiddleware`（本轮唯一允许的后端改动，仅限 CORS）
- 设置页完善：API 地址输入 + 测试连接 + 保存（`GET /health`）
- 端到端联调：建库 → 上传文档 → 轮询到 completed → 聊天问答
- 中文 UI 全量检查（菜单/按钮/表单/提示/空状态/状态标签/表格列名）
- 错误提示全量检查（含追踪编号）
- `README.md` 补充前端启动说明（`cd web && pnpm install && pnpm dev`）
- 检索测试标签页：确认后端无独立检索接口 → 显示"功能开发中"占位
- 修复联调发现的 bug

### 禁止实现内容
- ❌ 新增功能（仅联调与修复）
- ❌ 引入新的 UI 框架 / 状态库
- ❌ 自动化测试框架搭建（MVP 不强制，可视情况补少量测试）
- ❌ 暗色主题 / i18n / 移动端适配

### 验收标准
见 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` P1.5 节。

---

## 各批开始条件

| 批次 | 开始条件 |
|---|---|
| P1.0 | 后端 MVP 验收通过 + 用户确认进入前端阶段 |
| P1.1 | P1.0 验收通过 + 用户确认 |
| P1.2 | P1.1 验收通过 + 用户确认 |
| P1.3 | P1.2 验收通过 + 用户确认 |
| P1.4 | P1.3 验收通过 + 用户确认 |
| P1.5 | P1.4 验收通过 + 用户确认 |

---

## 暂缓项清单（前端 MVP 内禁止实现）

- 用户登录 / 权限管理
- 多知识库路由选择
- Rerank 模型配置界面
- 对话标题自动生成
- 文档删除 / 重新摄取（后端无接口）
- 知识库编辑 / 删除（后端无接口）
- 对话历史列表查询（后端未暴露 list 路由）
- 暗色主题
- 国际化（i18n）
- 移动端适配
- 自动化类型生成（OpenAPI → TypeScript）
- SSR / Nuxt / PWA
- 引用来源真实渲染（依赖后端 done 事件扩展 citations）
