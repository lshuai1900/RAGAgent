# Third Party Notices

## xerrors/Yuxi

- Source: `https://github.com/xerrors/Yuxi`
- Version: v0.7.0
- License: MIT
- Usage in RAGAgent:
  - selected frontend layout patterns
  - selected view structures
  - selected UI components
  - selected CSS styles
  - selected interaction patterns
- Adaptation scope:
  - lightweight RAG-only knowledge base workspace
  - dashboard
  - knowledge base list/detail
  - file management
  - document upload
  - retrieval test
  - chat QA
  - settings
- Explicit exclusions:
  - MCP
  - Skills
  - SubAgents
  - Sandbox
  - LangGraph orchestration
  - Knowledge Graph / Mind Map
  - RAG Evaluation
  - Multi-tenancy
  - Auth / JWT / Permission
  - Conversation history management
  - Model routing / fallback
  - Rerank configuration

## Yuxi MIT License

```
MIT License

Copyright (c) [xerrors](https://github.com/xerrors)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 复制 / 改造来源清单

Step 1–9 阶段在 `web/` 下复制或改造自 Yuxi v0.7.0 的文件，均保留文件头 MIT 归属注释。涉及视图与组件包括：YuxiAppShell / YuxiPageHeader / YuxiCard / YuxiEmptyState / YuxiStatusBadge 等基座组件，以及 DashboardView / KnowledgeBaseListView / KnowledgeBaseDetailView / FileManagerPanel / DocumentUploadModal / KbRetrievalTab / RagChatPanel / ChatMessageBubble / SourceReferenceCard 等页面与组件的布局、样式与交互实现。本项目仅复制并改造 Yuxi 在轻量 RAG-only 范围内的前端布局、组件、样式与交互，不复制或启用其 MCP、Skills、SubAgents、沙盒、LangGraph、多租户、权限、JWT、知识图谱、知识导图、RAG 评估、模型路由、Rerank 等重功能。

## 其他依赖

本项目前端使用的开源依赖（Vue 3、Vite、TypeScript、Ant Design Vue、Pinia、Vue Router、lucide-vue-next、dayjs 等）均遵循各自的开源协议，详见各依赖包的 LICENSE 文件。
