# AGENTS.md（前端）

> 本文件是 Ragent-Py **前端**（`web/`）AI 协作强约束指引。任何 AI 助手（含 Trae）在修改前端代码前必须先完整阅读本文件、`docs/FRONTEND_*.md` 与 `.trae/rules/frontend-*.mdc`。
>
> 后端规则见根目录 `/workspace/AGENTS.md`，本文件仅约束前端。

---

## 1. 前端定位

为 Ragent-Py 后端 MVP（知识库管理 + 文档摄取 + 流式问答）提供工程控制台风格 Web UI。

- 工程目录：`web/`
- 独立 `package.json`，不与后端共享依赖
- 只通过 HTTP 调用后端，不直接访问数据库 / 向量库 / 模型

---

## 2. 技术栈（锁定，不得擅自更换）

| 类别 | 选型 |
|---|---|
| 框架 | Vue 3（`<script setup>` Composition API） |
| 构建 | Vite 5+ |
| 语言 | TypeScript 5+（strict） |
| 路由 | Vue Router 4 |
| 状态管理 | Pinia |
| UI 组件库 | Ant Design Vue 4 |
| 图标 | lucide-vue-next |
| 时间 | dayjs |
| HTTP | 原生 fetch API |
| 包管理 | pnpm（推荐） |

---

## 3. 硬约束

### 3.1 中文 UI（最高优先级）
- 所有**用户可见文案**必须使用简体中文
- 包括：菜单、页面标题、按钮、表单 label、placeholder、loading、成功/错误提示、空状态、状态标签、表格列名、引用来源说明
- 后端枚举值（如 `pending` / `completed`）**禁止**原样展示，必须经中文映射
- 错误信息**禁止**原样抛英文，必须包装为中文 + 追踪编号

### 3.2 保持英文的范围
- 代码变量名、文件名、类型名、接口路径（如 `kb_id`、`/api/v1/chat/sse`）
- 状态机枚举值（仅作内部数据）
- trace_id（展示时前缀"追踪编号："，值保持原样）

### 3.3 禁止行为
- ❌ 禁止使用 React / Solid / Svelte
- ❌ 禁止使用 Tailwind CSS 作为主样式方案
- ❌ 禁止引入 axios（统一用 fetch）
- ❌ 禁止引入 Element Plus / Naive UI / Vuetify 等其他 UI 框架
- ❌ 禁止复制 [xerrors/Yuxi](https://github.com/xerrors/Yuxi) 仓库的任何源码
- ❌ 禁止中英混杂的可见文案
- ❌ 禁止把后端枚举值原样展示给用户
- ❌ 禁止前端直连 PostgreSQL / Milvus / Embedding API / LLM API
- ❌ 禁止前端存储 API Key / 数据库密码 / 模型密钥

### 3.4 只参考 Yuxi 的信息架构
- 只参考 Yuxi 的知识库列表 + 详情 + 标签页**产品结构与交互模式**
- 不复制其组件代码、样式、变量命名、目录结构
- Yuxi 使用 React，本项目使用 Vue 3，技术栈不同

---

## 4. 分批推进纪律（P1.0 - P1.5）

| 批次 | 范围 |
|---|---|
| P1.0 | 前端设计与规则落地（仅文档与规则，零业务代码） |
| P1.1 | Vue 项目骨架 + 布局 + 中文菜单 |
| P1.2 | 知识库列表页 + 新建知识库 |
| P1.3 | 知识库详情页 + 文件管理 + 上传文档 |
| P1.4 | 聊天问答 + POST SSE 流式输出 |
| P1.5 | 联调、中文 UI 验收、README 更新 |

### 4.1 推进规则
- **严格按 P1.0 → P1.5 顺序推进**
- 每批完成后必须通过 `docs/FRONTEND_ACCEPTANCE_CRITERIA.md` 对应批次验收
- 验收通过 + 用户确认后才能启动下一批
- **不允许一次性实现全部前端**

### 4.2 范围拦截
- 用户要求实现超出当前批次范围的功能 → 主动拒绝并提示当前批次范围
- 用户要求实现暂缓项 → 立即停止并说明该功能属于暂缓项

---

## 5. 前后端对接边界

### 5.1 只调用 FastAPI 后端
- 前端只调用 `docs/FRONTEND_API_CONTRACT.md` 列出的接口
- API Base URL 从 localStorage 读取（key：`ragent.apiBaseUrl`），默认 `http://localhost:8000`

### 5.2 禁止直连
- PostgreSQL / Milvus / Embedding API / LLM API 全部由后端编排，前端不直连

### 5.3 统一响应解析
- 非 SSE 接口：解析 `ApiResponse<T>`（`code`/`message`/`data`/`trace_id`）
- `code === 0` 取 `data`；`code !== 0` 抛错，展示中文 `message` + 追踪编号
- SSE 接口（`POST /api/v1/chat/sse`）：用 fetch + ReadableStream 解析 start/delta/done/error，**禁用 EventSource**

---

## 6. 暂缓项清单（前端 MVP 内禁止实现）

- 用户登录 / 权限管理
- 多知识库路由选择
- Rerank 模型配置界面
- 对话标题自动生成
- 文档删除 / 重新摄取（后端无接口）
- 知识库编辑 / 删除（后端无接口）
- 对话历史列表查询（后端未暴露 list 路由）
- 暗色主题
- 国际化（i18n，MVP 锁定简体中文）
- 移动端适配（MVP 仅保证桌面端）
- 自动化类型生成（OpenAPI → TypeScript）
- SSR / Nuxt / PWA / 微前端
- 引用来源真实渲染（依赖后端 done 事件扩展 citations）

---

## 7. 编码规范要点

- Vue 3 `<script setup lang="ts">` Composition API
- 组件命名：PascalCase（如 `KbCard.vue`、`CreateKbModal.vue`）
- props/emits 用 TypeScript 类型注解，不用运行时默认值对象堆砌
- 路径别名 `@/` → `src/`
- 状态展示类组件接收枚举值，内部做中文映射
- views 不直接调 api（经 store 或 composables）
- utils 不调 api、不访问 store（纯函数）
- 错误提示统一用 Ant Design Vue 的 `message.error`，附追踪编号

---

## 8. 提交规范

Conventional Commits，scope 用前端模块名：

```
feat(web): 实现知识库列表页
feat(web): 实现聊天问答 SSE 流式输出
fix(web): 修复文档状态轮询不停止
docs(web): 更新前端启动说明
chore(web): 升级 ant-design-vue 至 4.x
```

---

## 9. 参考文档

- 前端 UI 设计：`docs/FRONTEND_UI_SPEC.md`
- 前端架构：`docs/FRONTEND_ARCHITECTURE.md`
- 前后端 API 契约：`docs/FRONTEND_API_CONTRACT.md`
- 任务拆分：`docs/FRONTEND_TASK_PLAN.md`
- 验收标准：`docs/FRONTEND_ACCEPTANCE_CRITERIA.md`
- 后端规则：`/workspace/AGENTS.md`
- Yuxi（仅参考信息架构）：https://github.com/xerrors/Yuxi
