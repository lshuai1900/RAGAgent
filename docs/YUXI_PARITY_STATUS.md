# Yuxi 风格复刻状态（YUXI_PARITY_STATUS）

本文件记录 RAGAgent 前端在轻量 RAG-only 范围内对 xerrors/Yuxi v0.7.0 的复刻范围与当前实现状态。复刻原则：复制并改造 Yuxi 的布局、组件、样式与交互，用于对齐 RAGAgent 已实现功能的 UI；不复制或启用 Yuxi 的 Agent Harness、MCP、Skills、SubAgents、Sandbox、多租户、权限、知识图谱、RAG 评估等重功能。

授权说明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

## 1. 已复刻页面与组件

### 1.1 基座组件（`web/src/components/yuxi/`）

| �件 | 复刻内容 |
|---|---|
| YuxiAppShell.vue | 左侧导航 + 顶部标题区 + 主内容区工作台壳子 |
| YuxiPageHeader.vue | sticky + blur 顶部标题栏 |
| YuxiCard.vue | 卡片容器（标题 + body + 边框 + 圆角） |
| YuxiEmptyState.vue | 空状态（图标 + 标题 + 描述 + 可选 action） |
| YuxiStatusBadge.vue | 状态徽标（processing / success / error / default） |

### 1.2 视图（`web/src/views/`）

| 视图 | 复刻内容 |
|---|---|
| DashboardView.vue | 仪表盘健康检查（YuxiPageHeader + YuxiCard 状态卡） |
| KnowledgeBaseListView.vue | 知识库卡片网格 + 新建弹窗 |
| KnowledgeBaseDetailView.vue | 沉浸式详情壳子（Header + 子路由 Tabs） |
| knowledge-base/KbFilesTab.vue | 文件管理 Tab（列表 + 轮询 + 操作） |
| knowledge-base/KbRetrievalTab.vue | 检索测试 Tab（左右分栏 + SSE + 引用来源） |
| knowledge-base/KbChatTab.vue | 聊天问答 Tab（嵌入式 RagChatPanel） |
| ChatView.vue | 顶层 /chat（知识库选择器 + RagChatPanel） |
| SettingsView.vue | 设置（API Base URL + 测试连接） |

### 1.3 功能组件（`web/src/components/`）

| 组件 | 复刻内容 |
|---|---|
| FileManagerPanel.vue | 文件管理面板（toolbar + 状态过滤 + loading/empty/error） |
| DocumentTable.vue | 文件行列表 + 关键字 + 状态过滤 |
| FileListItem.vue | 文件行（图标 + 名 + 元信息 + 状态徽标 + 操作菜单） |
| DocumentUploadModal.vue | Yuxi 风格 dropzone + 文件预览 + 校验 |
| DocumentRenameModal.vue | 重命名弹窗 |
| FileTypeIcon.vue | 文件类型徽标（TXT / MD / PDF） |
| KnowledgeBaseCard.vue | 知识库卡片 |
| KnowledgeBaseCreateModal.vue | 新建知识库弹窗 |
| KnowledgeBaseEditModal.vue | 编辑 + 删除知识库弹窗 |
| KnowledgeBaseDetailHeader.vue | 详情页沉浸式 Header |
| KnowledgeBaseTabs.vue | 详情页 Tab 导航（3 个真实 Tab） |
| chat/RagChatPanel.vue | RAG 聊天面板（本地消息 + SSE + AbortController） |
| chat/ChatMessageBubble.vue | 聊天消息气泡（user / assistant） |
| chat/SourceReferenceCard.vue | 引用来源卡片（标题 + 内容 + 相似度） |

## 2. 已复刻交互

- 仪表盘健康检查与重新检查
- API Base URL 设置 + 测试连接（写入 localStorage）
- 创建 / 编辑 / 删除知识库
- 知识库卡片进入详情
- 详情页 Tab 切换（文件管理 / 检索测试 / 聊天问答）
- 文件上传（拖拽 + 格式 / 大小 / 重名校验）
- 文档状态轮询（3 秒，非终态触发，全终态停止）
- 文件重命名 / 删除 / 重新处理
- 检索测试 POST SSE 流式输出
- 聊天问答 POST SSE 流式输出
- 停止生成（AbortController）
- 清空当前页面对话
- citations → references 前端统一映射
- 引用来源卡片展示（相似度 3 位小数 + 内容折叠）
- trace_id / finish_reason 展示
- 中文错误提示 + 追踪编号

## 3. 排除项（暂缓 / 未复刻）

以下功能不属于本次复刻范围，未在 UI 暴露入口：

- MCP 工具集成
- Skills / SubAgents / Sandbox
- LangGraph 多智能体编排
- 知识图谱 / 知识导图
- RAG 评估 / 评估基准
- 多租户
- 登录 / JWT / 权限
- 会话历史管理（聊天消息仅保存在页面内存）
- 模型路由 / 降级
- Rerank 配置
- Markdown 富文本渲染
- Office / 图片 / CSV / JSON / HTML 等更多文件格式解析
- Agent Harness / Tool 调用面板 / artifact 卡片

前端 feature flags（`web/src/config/features.ts`）中所有暂缓项默认为 `false`，确保运行时用户完全看不到暂缓功能入口。

## 4. SSE 与引用来源复用

为避免重复实现，SSE 客户端与引用映射逻辑统一为单套：

| 模块 | 职责 |
|---|---|
| `api/chat.ts` `streamChatSse` | fetch + ReadableStream，解析 start / delta / done / error |
| `utils/sse.ts` `parseSseStream` | SSE 帧解析（兼容多事件 chunk） |
| `utils/chatReferences.ts` `mapCitationsToReferences` | citations / references / retrieval_context → UiChatReference[] |
| `utils/apiErrors.ts` `formatChatStreamError` | 聊天 / 检索 SSE 错误中文映射 |
| `components/chat/SourceReferenceCard.vue` | 引用来源卡片（被检索测试与聊天复用） |

检索测试页（KbRetrievalTab）与聊天面板（RagChatPanel）均复用上述模块，无两套独立 SSE / 引用 / 错误逻辑。

## 5. 验收命令

```bash
cd web
npm run build
cd ..
make lint          # ruff check + ruff format --check
make typecheck     # mypy src/ragent
make test-unit     # pytest tests/unit
```

当前状态：四项命令均通过。

## 6. 已清理的旧组件

Step 9 已删除以下无引用的旧组件与 store：

- `components/SearchTestPanel.vue`
- `components/ChatSsePanel.vue`
- `components/RetrievalContextPanel.vue`
- `components/DocumentStatusCards.vue`
- `stores/chat.ts`
