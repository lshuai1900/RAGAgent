# FRONTEND_ACCEPTANCE_CRITERIA.md

> Ragent-Py 前端每批验收标准（P1.0 - P1.5）
>
> 每批完成后必须逐条对照本文件验收，全部通过才能启动下一批。

---

## 通用验收维度

每个批次除特定验收项外，均须满足以下通用维度：

| 维度 | 通用要求 |
|---|---|
| 中文 UI | 所有用户可见文案为简体中文，无中英混杂 |
| 不越界 | 未实现本批次禁止内容，未实现暂缓项 |
| 工程控制台风格 | 浅色、细边框、高信息密度，无营销页风格 |
| 错误提示 | 错误提示为中文，附追踪编号（trace_id 非空时） |
| 枚举映射 | 后端枚举值经中文映射后展示，不原样抛给用户 |

---

## P1.0　前端设计与规则落地

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.0-1 | 文档齐全 | 5 个 docs 文件全部创建：UI_SPEC / ARCHITECTURE / API_CONTRACT / TASK_PLAN / ACCEPTANCE_CRITERIA |
| P1.0-2 | 前端 AI 规则 | `web/AGENTS.md` 创建，明确技术栈、中文要求、分批纪律、不复制 Yuxi |
| P1.0-3 | Trae 规则齐全 | 6 个 `.trae/rules/frontend-*.mdc` 全部创建 |
| P1.0-4 | API 契约准确 | `FRONTEND_API_CONTRACT.md` 接口与后端 `src/ragent/api/v1/` 实际路由一一对应 |
| P1.0-5 | ApiResponse 结构正确 | 契约中 `code/message/data/trace_id` 四字段与后端 `framework/core/response.py` 一致 |
| P1.0-6 | SSE 事件定义准确 | start/delta/done/error 四类事件结构与后端 `framework/sse/emitter.py` 一致 |
| P1.0-7 | 文档状态映射完整 | pending/parsing/chunking/embedding/indexing/completed/failed 七态全部有中文文案 |
| P1.0-8 | 任务分批清晰 | P1.0-P1.5 每批有目标、允许内容、禁止内容、验收标准 |
| P1.0-9 | 引用来源限制说明 | 文档明确指出当前后端 done 事件不携带 citations，前端 MVP 占位处理 |
| P1.0-10 | CORS 说明 | 文档说明后端未配置 CORS，P1.5 联调阶段补 |
| P1.0-11 | 零业务代码 | `web/` 下无 `package.json` / Vue 文件 / TS 业务代码 |
| P1.0-12 | 后端零改动 | `src/ragent/` 无任何改动 |

### 验收方式
- 文件存在性检查（LS / Glob）
- 文档内容人工审阅
- 与后端代码交叉核对（API 路由、ApiResponse、SSE 事件、文档状态枚举）

---

## P1.1　Vue 项目骨架 + 布局 + 中文菜单

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.1-1 | 工程可启动 | `cd web && pnpm install && pnpm dev` 成功启动，浏览器可访问 |
| P1.1-2 | 技术栈符合 | package.json 依赖含 vue / vue-router / pinia / ant-design-vue / lucide-vue-next / dayjs，无 React / axios / Tailwind |
| P1.1-3 | TypeScript strict | `tsconfig.json` 开启 `strict: true`，`pnpm build` 无类型错误 |
| P1.1-4 | 路由表完整 | 4 条路由：`/` / `/knowledge-bases/:kbId` / `/settings` / `/:pathMatch(.*)*`，未匹配跳 404 |
| P1.1-5 | 全局布局 | `DefaultLayout.vue` 含顶部导航 + `<router-view />` |
| P1.1-6 | 中文菜单 | 顶部导航标题"RAGAgent 控制台"，菜单项"知识库""设置"全中文 |
| P1.1-7 | settings store | `apiBaseUrl` 从 localStorage 读取，默认 `http://localhost:8000`，修改时写回 |
| P1.1-8 | client 封装 | `api/client.ts` 实现 baseUrl 拼接 + ApiResponse 解析 + 错误处理（code≠0 抛 ApiError） |
| P1.1-9 | health 客户端 | `api/health.ts` 调 `GET /health`，解析 ApiResponse |
| P1.1-10 | 类型定义 | `types/api.ts` 含 ApiResponse / PageResponse / 各 DTO；`types/enums.ts` 含文档/知识库状态枚举 |
| P1.1-11 | 中文映射 | `utils/format.ts` 含文档状态中文映射、文件大小/时间格式化 |
| P1.1-12 | 404 中文 | NotFound 页文案全中文，有"返回首页"按钮 |
| P1.1-13 | 业务页占位 | List/Detail/Settings 页面仅占位标题，无业务实现 |
| P1.1-14 | 不越界 | 无知识库卡片、上传、聊天、SSE 代码 |

### 验收方式
- `pnpm dev` 启动并人工浏览
- `pnpm build` 通过
- 代码审阅（store / client / router）

---

## P1.2　知识库列表页 + 新建知识库

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.2-1 | 列表加载 | 进入 `/` 自动调 `GET /api/v1/knowledge-bases`，展示卡片网格 |
| P1.2-2 | 卡片展示 | 每张卡片含名称、描述、文档数、状态标签、创建时间 |
| P1.2-3 | 状态中文映射 | `active`→"启用"（绿）、`archived`→"已归档"（灰） |
| P1.2-4 | 空状态 | 无知识库时展示"暂无知识库，点击右上角新建" |
| P1.2-5 | 新建弹窗 | 点"新建知识库"打开 Modal，表单含名称/描述/分块策略/分块大小/分块重叠 |
| P1.2-6 | 表单校验 | 名称必填（1-128）；分块重叠 < 分块大小；前端拦截不发非法请求 |
| P1.2-7 | Embedding 只读 | embedding_model / embedding_dim 用默认值，不让用户填错 |
| P1.2-8 | 创建成功 | 提交 `POST /api/v1/knowledge-bases` 成功后刷新列表，提示"知识库创建成功" |
| P1.2-9 | 创建失败 | code≠0 时 `message.error` 展示中文 message + 追踪编号 |
| P1.2-10 | 卡片跳转 | 点卡片跳 `/knowledge-bases/:kbId`（详情页可仍为占位） |
| P1.2-11 | loading 态 | 列表加载时显示"加载中…" |
| P1.2-12 | 网络错误 | 后端不可达时提示"连接后端失败，请检查 API 地址设置" |
| P1.2-13 | 不越界 | 无文档管理、上传、聊天、SSE 代码 |

### 验收方式
- 启动后端 + 前端，人工建库、看列表
- 故意填错表单看校验
- 断开后端看错误提示

---

## P1.3　知识库详情页 + 文件管理 + 上传文档

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.3-1 | 详情页框架 | 顶部展示知识库名称/描述/文档数/状态/创建时间，含"← 返回"按钮 |
| P1.3-2 | 标签页 | Tabs 含"文件管理""检索测试""聊天问答""配置"，默认"文件管理" |
| P1.3-3 | tab 同步 URL | 切换标签页同步 `route.query.tab`，刷新保持标签 |
| P1.3-4 | 文档表格 | 列名全中文：文档名称/类型/大小/状态/创建时间/操作 |
| P1.3-5 | 状态统计 | 顶部按文档状态分组计数（待处理/处理中/已完成/失败） |
| P1.3-6 | 状态 Tag | 七态全部有中文文案 + 颜色（见 UI 规范第 8 节） |
| P1.3-7 | 上传弹窗 | 点"上传文档"打开 Modal，选文件 + 确认 |
| P1.3-8 | 大小校验 | 前端先校验 ≤50MB，超限提示不发请求 |
| P1.3-9 | FormData 上传 | 用 FormData 提交 `POST /api/v1/documents/upload`，不手设 Content-Type |
| P1.3-10 | 上传成功 | 返回 document_id 后刷新表格，提示"文档上传成功" |
| P1.3-11 | 重复文件 | `duplicated===true` 提示"文件已存在，已复用已有文档" |
| P1.3-12 | 状态轮询 | 存在非终态文档时每 3 秒轮询；全终态后停止；卸载时停止 |
| P1.3-13 | 轮询可见 | pending→parsing→...→completed 状态变化在表格实时更新 |
| P1.3-14 | 失败展示 | status=failed 时展示 error_message（中文友好） |
| P1.3-15 | 占位标签 | 检索测试/聊天问答/配置标签页占位"功能开发中" |
| P1.3-16 | 不越界 | 无 SSE、无删除调用、无检索调用 |

### 验收方式
- 建库后上传 txt/md/pdf 各一个，观察状态流转
- 上传超大文件看校验
- 重复上传同文件看 duplicated 提示
- 切换标签页看 URL 同步

---

## P1.4　聊天问答 + POST SSE 流式输出

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.4-1 | SSE 客户端 | `api/chat.ts` 用 fetch + ReadableStream，**禁用 EventSource** |
| P1.4-2 | 请求体 | POST JSON，含 session_id/kb_id/question/top_k 等，Content-Type: application/json |
| P1.4-3 | 事件解析 | 正确解析 start/delta/done/error 四类事件，忽略 ping 等非约定事件 |
| P1.4-4 | session_id | 前端用 crypto.randomUUID 生成，"新建对话"重置 |
| P1.4-5 | 流式输出 | 收到 delta 逐字追加到助手消息，视觉可见逐字效果 |
| P1.4-6 | 思考态 | 发送后、首个 delta 前显示"正在思考…" |
| P1.4-7 | 完成态 | 收到 done 后停止接收，输入框恢复可用 |
| P1.4-8 | 错误事件 | 收到 error 事件展示中文 message + "追踪编号：{trace_id}" |
| P1.4-9 | 网络错误 | fetch 失败提示"连接后端失败，请检查 API 地址设置" |
| P1.4-10 | 流中断 | 未收到 done/error 即结束，提示"回答中断，请重试" |
| P1.4-11 | 输入禁用 | 发送中输入框 + 发送按钮禁用，避免重复发送 |
| P1.4-12 | 知识库选择 | 顶部下拉固定为当前知识库（详情页带入） |
| P1.4-13 | 引用占位 | 引用来源区域显示"本次回答无引用来源"（后端 done 无 citations） |
| P1.4-14 | 中文 UI | 用户/助手标签、发送按钮、空状态全中文 |
| P1.4-15 | 不越界 | 无引用真实渲染、无对话历史持久化查询、无标题生成 |

### 验收方式
- 知识库内有已完成文档，提问看流式输出
- 故意输空问题看前端拦截
- 后端停服看网络错误
- 检查 `api/chat.ts` 源码确认无 EventSource

---

## P1.5　联调、中文 UI 验收、README 更新

### 验收清单

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| P1.5-1 | 后端 CORS | 后端 `main.py` 补 `CORSMiddleware`，前端跨域请求成功 |
| P1.5-2 | 端到端流程 | 建库 → 上传文档 → 轮询到 completed → 聊天问答 流式回答 全程打通 |
| P1.5-3 | 设置页可用 | API 地址输入 + 测试连接（GET /health）+ 保存 localStorage |
| P1.5-4 | 测试连接反馈 | 成功显示"连接正常"，失败显示中文错误 |
| P1.5-5 | 中文 UI 全量 | 菜单/按钮/表单/placeholder/loading/成功提示/错误提示/空状态/状态标签/表格列名 全中文 |
| P1.5-6 | 错误提示全量 | 所有错误提示含追踪编号（trace_id 非空时） |
| P1.5-7 | 不越界 | 未实现暂缓项（登录/多知识库路由/Rerank 配置/删除/标题生成等） |
| P1.5-8 | 检索测试可用 | 检索测试标签页为真实功能（P1.4-B 已实现，复用 `POST /api/v1/chat/sse`，展示回答与引用来源或"暂无引用来源"） |
| P1.5-9 | README 更新 | `README.md` 补充前端启动说明（cd web / pnpm install / pnpm dev） |
| P1.5-10 | 生产构建 | `pnpm build` 成功，`pnpm preview` 可预览 |
| P1.5-11 | 联调 bug 修复 | 联调发现的问题已修复 |

### 验收方式
- 完整端到端操作一遍
- 切换中文输入法扫一遍所有页面文案
- `pnpm build` 通过
- 人工审阅 README

---

## 不越界验收（每批通用）

每批验收时必须确认以下"不越界"项：

| 检查项 | 标准 |
|---|---|
| 未实现暂缓项 | 无登录/多知识库路由/Rerank/删除/标题生成/i18n/暗色主题/移动端 |
| 未跨批次 | 未提前实现后续批次功能 |
| 未复制 Yuxi | 无 Yuxi 仓库源码片段、组件命名、CSS 类名 |
| 未引入禁用库 | 无 React / axios / Tailwind（主样式）/ Element Plus / Naive UI |
| 未直连基础设施 | 前端无 PostgreSQL / Milvus / Embedding / LLM 直连代码 |
| 未存敏感信息 | localStorage 仅存 `ragent.apiBaseUrl`，无 API Key |
