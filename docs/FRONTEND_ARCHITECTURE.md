# FRONTEND_ARCHITECTURE.md

> Ragent-Py 前端架构与目录结构规范（P1.0）
>
> 本文件定义 `web/` 前端工程的目录结构、技术栈、分层职责与对接边界。
> UI 设计见 `docs/FRONTEND_UI_SPEC.md`，接口契约见 `docs/FRONTEND_API_CONTRACT.md`。

---

## 1. 技术栈（锁定，不得擅自更换）

| 类别 | 选型 |
|---|---|
| 框架 | Vue 3（`<script setup>` Composition API） |
| 构建工具 | Vite 5+ |
| 语言 | TypeScript 5+（strict 模式） |
| 路由 | Vue Router 4 |
| 状态管理 | Pinia |
| UI 组件库 | Ant Design Vue 4 |
| 图标 | lucide-vue-next |
| 时间处理 | dayjs |
| HTTP 客户端 | 原生 fetch API（不引入 axios） |
| 包管理 | pnpm（推荐）/ npm |

### 1.1 选型约束
- ❌ 禁止使用 React / Solid / Svelte
- ❌ 禁止使用 Tailwind CSS 作为主样式方案（MVP 用 Ant Design Vue 默认样式 + 少量 scoped CSS / CSS Module）
- ❌ 禁止引入 axios（统一用 fetch）
- ❌ 禁止引入 Element Plus / Naive UI / Vuetify 等其他 UI 框架
- ❌ 禁止引入 Lodash 全量包（按需引入子模块或手写工具函数）

---

## 2. 前后端对接边界（硬约束）

### 2.1 前端只调用 FastAPI 后端
前端**只**通过 HTTP 调用 `docs/FRONTEND_API_CONTRACT.md` 中列出的接口，由后端统一编排数据库 / 向量库 / 模型。

### 2.2 禁止直接访问的基础设施
前端**禁止**直接访问以下任何一项：
- PostgreSQL（不直连数据库）
- Milvus（不直连向量库）
- Embedding API（不直接调用模型供应商的向量化接口）
- LLM API（不直接调用模型供应商的对话接口）

> 理由：这些能力由后端编排，前端直连会绕过 trace_id 透传、异常包装、配置管理，破坏后端分层边界。

### 2.3 API Base URL
- 从 localStorage 读取，key 为 `ragent.apiBaseUrl`
- 默认值：`http://localhost:8000`
- 用户可在"设置"页修改并保存
- 所有请求基于该 Base URL 拼接相对路径（如 `${baseUrl}/api/v1/knowledge-bases`）

### 2.4 不存敏感信息
- 前端**不存储**任何 API Key / 数据库密码 / 模型密钥
- 模型密钥由后端 `ModelProvider.api_key_ref` 管理，前端无感知
- localStorage 只存 `ragent.apiBaseUrl`（非敏感）

---

## 3. web/ 目录结构

```
web/
├── AGENTS.md                    # 前端 AI 协作规则
├── index.html                   # Vite 入口 HTML
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts
├── env.d.ts                     # Vite 环境变量类型
├── public/
│   └── favicon.svg
└── src/
    ├── main.ts                  # 应用入口（挂载 Pinia + Router + Antd）
    ├── App.vue                  # 根组件（仅 <router-view />）
    ├── router/
    │   └── index.ts             # 路由表（createRouter + createWebHistory）
    ├── stores/                  # Pinia store
    │   ├── settings.ts          # 设置（apiBaseUrl 等）
    │   ├── knowledgeBase.ts     # 知识库列表/详情状态
    │   └── chat.ts              # 对话会话状态（session_id、消息列表）
    ├── api/                     # API 客户端（统一 fetch 封装）
    │   ├── client.ts            # 基础 fetch 封装（baseUrl、ApiResponse 解析、错误处理）
    │   ├── health.ts            # GET /health
    │   ├── knowledgeBase.ts     # 知识库 CRUD
    │   ├── document.ts          # 文档上传/列表/查询
    │   └── chat.ts              # SSE 流式问答（fetch + ReadableStream）
    ├── types/                   # TypeScript 类型定义
    │   ├── api.ts               # ApiResponse<T>、分页、各接口 DTO 类型
    │   └── enums.ts             # 枚举常量（文档状态、知识库状态等）
    ├── layouts/
    │   └── DefaultLayout.vue    # 顶部导航 + <router-view />
    ├── views/                   # 页面级组件（与路由一一对应）
    │   ├── knowledge-base/
    │   │   ├── List.vue         # 知识库列表页
    │   │   └── Detail.vue       # 知识库详情页（含标签页）
    │   ├── settings/
    │   │   └── Index.vue        # 设置页
    │   └── NotFound.vue         # 404 页
    ├── components/              # 可复用业务组件
    │   ├── knowledge-base/
    │   │   ├── KbCard.vue       # 知识库卡片
    │   │   └── CreateKbModal.vue# 新建知识库弹窗
    │   ├── document/
    │   │   ├── UploadModal.vue  # 上传文档弹窗
    │   │   ├── DocumentTable.vue# 文档表格
    │   │   └── StatusTag.vue    # 状态标签（中文映射）
    │   └── chat/
    │       ├── ChatPanel.vue    # 聊天主面板
    │       ├── MessageItem.vue  # 单条消息
    │       └── CitationList.vue # 引用来源列表
    ├── composables/             # 组合式函数
    │   ├── useApiBaseUrl.ts     # 读写 localStorage 的 baseUrl
    │   ├── useSseChat.ts        # SSE 流式问答封装（fetch + ReadableStream）
    │   └── usePolling.ts        # 文档状态轮询
    ├── utils/                   # 纯工具函数
    │   ├── format.ts            # 文件大小、时间、状态文案映射
    │   └── uuid.ts              # session_id 生成
    └── assets/
        └── styles/
            └── global.css       # 全局轻量样式（仅工程控制台风格调整）
```

> 上述结构为 P1.0 设计目标。实际文件在 P1.1-P1.5 各批次中按 `docs/FRONTEND_TASK_PLAN.md` 分批创建，**禁止一次性创建全部文件**。

---

## 4. 各层职责

### 4.1 api/（API 客户端）
- `client.ts`：封装统一 fetch，负责拼接 baseUrl、设置请求头、解析 `ApiResponse<T>`、统一错误处理
- 每个业务文件（`knowledgeBase.ts` / `document.ts` / `chat.ts` / `health.ts`）导出与后端接口一一对应的函数
- **SSE 接口**（`chat.ts`）使用 fetch + ReadableStream，**禁止**用 `EventSource`
- 只负责"请求与响应解析"，不持有业务状态

### 4.2 stores/（Pinia 状态管理）
- `settings.ts`：管理 `apiBaseUrl`（初始化时从 localStorage 读取，修改时同步写回）
- `knowledgeBase.ts`：知识库列表缓存、当前详情知识库、加载状态
- `chat.ts`：当前会话 `session_id`、消息列表、流式接收中的临时状态
- store 只调用 `api/`，不直接发 fetch（保持单一职责）

### 4.3 views/（页面级组件）
- 与路由表一一对应
- 负责页面级编排：调 store / composables → 组合 components → 渲染
- **禁止**在 views 中直接调用 `api/`（必须经 store 或 composables）
- **禁止**在 views 中硬编码接口路径

### 4.4 components/（可复用业务组件）
- 按业务域分子目录（knowledge-base / document / chat）
- 组件通过 `props` 接收数据，通过 `emits` 抛事件，**不直接调 api**
- 状态展示类组件（如 `StatusTag`）接收枚举值，内部做中文映射

### 4.5 composables/（组合式函数）
- `useApiBaseUrl.ts`：封装 localStorage 读写 + 默认值兜底
- `useSseChat.ts`：封装 SSE 流式问答的 fetch + ReadableStream 解析逻辑，返回响应式状态（连接中/接收中/完成/错误 + 累积内容 + trace_id）
- `usePolling.ts`：封装轮询（启动/停止/条件终止），用于文档状态轮询

### 4.6 layouts/（布局组件）
- `DefaultLayout.vue`：顶部导航 + `<router-view />`，所有页面共享
- 顶部导航包含 Logo、标题"RAGAgent 控制台"、"设置"入口

### 4.7 router/（路由）
- `createRouter` + `createWebHistory`
- 路由表见 `docs/FRONTEND_UI_SPEC.md` 第 5 节
- 详情页标签页通过 `route.query.tab` 同步

### 4.8 utils/（纯工具函数）
- `format.ts`：文件大小、时间、状态文案映射（无副作用纯函数）
- `uuid.ts`：`session_id` 生成（优先 `crypto.randomUUID`）
- **禁止**在 utils 中调用 api 或访问 store

### 4.9 types/（类型定义）
- `api.ts`：`ApiResponse<T>`、`PageResponse<T>`、各接口请求/响应 DTO 类型（与后端 schema 对齐）
- `enums.ts`：文档状态、知识库状态等枚举常量（与后端 `domain/enums.py` 值对齐，**仅作常量，不依赖后端代码**）

---

## 5. 数据流

### 5.1 普通请求（以创建知识库为例）
```
CreateKbModal.vue
   │ emits('submit', form)
   ▼
views/knowledge-base/List.vue
   │ 调 store.createKb(form)
   ▼
stores/knowledgeBase.ts
   │ 调 api.createKnowledgeBase(form)
   ▼
api/knowledgeBase.ts
   │ fetch POST {baseUrl}/api/v1/knowledge-bases
   │ 解析 ApiResponse<KnowledgeBaseOut>
   ▼
api/client.ts（统一 fetch 封装 + 错误处理）
```

### 5.2 SSE 流式问答
```
ChatPanel.vue
   │ 调 useSseChat().send({ session_id, kb_id, question, ... })
   ▼
composables/useSseChat.ts
   │ 调 api.chatSse(payload, { onDelta, onDone, onError })
   ▼
api/chat.ts
   │ fetch POST {baseUrl}/api/v1/chat/sse
   │ body: JSON, headers: { Accept: text/event-stream }
   │ reader = response.body.getReader()
   │ 解析 SSE 事件流：start / delta / done / error
   │ 通过回调把 delta 推回 composable
```

### 5.3 错误传播
- `api/client.ts` 解析响应：
  - HTTP 非 2xx → 抛 `ApiError`（含 code / message / trace_id）
  - HTTP 2xx 但 `code !== 0` → 抛 `ApiError`（含 code / message / trace_id）
  - 网络异常 → 抛 `NetworkError`（中文文案"连接后端失败"）
- views / components 捕获后用 `message.error` 展示中文 + 追踪编号

---

## 6. 统一响应解析规则

后端所有非 SSE 接口返回 `ApiResponse<T>`：
```json
{
  "code": 0,
  "message": "OK",
  "data": { ... },
  "trace_id": "xxx"
}
```

前端 `api/client.ts` 解析规则：
1. `code === 0` → 返回 `data`（业务数据）
2. `code !== 0` → 抛 `ApiError`，`message` 作为用户可见错误文案，`trace_id` 作为追踪编号
3. HTTP 状态码非 2xx → 抛 `ApiError`（尝试从 body 解析 code/message/trace_id，失败则用通用中文文案）

> SSE 接口（`POST /api/v1/chat/sse`）**不走**此解析规则，事件流解析见 `.trae/rules/frontend-sse.mdc`。

---

## 7. 构建与开发

### 7.1 开发命令（P1.1 起启用）
```bash
cd web
pnpm install
pnpm dev          # 启动 Vite dev server（默认 5173）
pnpm build        # 生产构建到 web/dist
pnpm preview      # 预览生产构建
```

### 7.2 开发期后端代理（可选）
- 开发期可通过 Vite `server.proxy` 把 `/api` 代理到 `http://localhost:8000`，避免 CORS
- 但生产部署仍需后端配置 CORS 或同源部署
- 代理配置仅在 `vite.config.ts` 中，不替代 localStorage 的 `apiBaseUrl`（用户仍可在设置页修改）

### 7.3 TypeScript 配置
- `strict: true`
- 路径别名：`@/` → `src/`
- 目标：`ES2020` + `DOM` + `DOM.Iterable`

---

## 8. 与后端工程的关系

```
/workspace
├── src/ragent/          # 后端（FastAPI）
├── web/                 # 前端（Vue 3）—— 本规范覆盖范围
├── docs/                # 文档（前后端共享）
└── .trae/rules/         # 规则（前后端各自子集）
```

- 前端独立工程，独立 `package.json`，不与后端共享依赖
- 前端不导入后端任何 Python 代码
- 前端类型定义（`types/api.ts`）**手工对齐**后端 schema，不自动生成（MVP 取舍）
- 后端 `docs/FRONTEND_API_CONTRACT.md` 是前后端对接的唯一契约源

---

## 9. 不在本架构范围内（暂缓）

- 自动化类型生成（OpenAPI → TypeScript）
- 前端单元测试框架搭建（MVP 不强制，P1.5 视情况补充）
- PWA / Service Worker
- SSR / Nuxt
- 微前端
- 国际化（i18n）
