# FRONTEND_API_CONTRACT.md

> Ragent-Py 前后端 API 契约（P1.0）
>
> 本文件是前端与后端对接的**唯一契约源**。前端 `web/src/api/` 的实现必须严格遵循本文件，不得自行推断接口形态。
> 后端实现见 `src/ragent/api/v1/` 与 `src/ragent/schemas/`。

---

## 1. 通用约定

### 1.1 Base URL
- 前端从 localStorage 读取 `ragent.apiBaseUrl`，默认 `http://localhost:8000`
- 所有接口路径基于该 Base URL 拼接

### 1.2 统一响应体 ApiResponse<T>

后端所有**非 SSE** 接口返回如下结构：

```json
{
  "code": 0,
  "message": "OK",
  "data": { ... },
  "trace_id": "1782633641000-abc123"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `int` | `0` 表示成功；非 `0` 表示错误（按错误码段位区分异常类型） |
| `message` | `string` | 响应消息；错误时为用户可见错误信息，**不含堆栈** |
| `data` | `T \| null` | 业务数据；错误时为 `null` |
| `trace_id` | `string` | 链路追踪 ID，用于问题定位 |

### 1.3 分页响应结构

分页接口的 `data` 为：
```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 1.4 错误码段位（与后端 `framework/core/exceptions.py` 对齐）

| 段位 | 异常类型 | 前端处理建议 |
|---|---|---|
| `1xxxx` | BizException（业务异常） | 直接展示 `message` |
| `2xxxx` | SysException（系统异常） | 展示 `message` + 追踪编号 |
| `3xxxx` | InfraException（基础设施异常） | 展示通用文案"服务暂不可用"+ 追踪编号 |

> 前端**不需要**区分具体段位，统一规则：`code !== 0` 即视为错误，展示 `message`，附加"追踪编号：{trace_id}"。

---

## 2. 接口清单

| 方法 | 路径 | 用途 | 响应类型 |
|---|---|---|---|
| GET | `/health` | 健康检查（测试连接用） | `ApiResponse[HealthResponse]` |
| POST | `/api/v1/knowledge-bases` | 创建知识库 | `ApiResponse[KnowledgeBaseOut]` |
| GET | `/api/v1/knowledge-bases` | 分页列出知识库 | `ApiResponse[KnowledgeBasePage]` |
| GET | `/api/v1/knowledge-bases/{kb_id}` | 查询单个知识库 | `ApiResponse[KnowledgeBaseOut]` |
| POST | `/api/v1/documents/upload` | 上传文档（multipart） | `ApiResponse[DocumentUploadResponse]` |
| GET | `/api/v1/documents` | 分页列出文档（可按 kb_id 过滤） | `ApiResponse[DocumentPage]` |
| GET | `/api/v1/documents/{document_id}` | 查询单个文档状态 | `ApiResponse[DocumentOut]` |
| POST | `/api/v1/chat/sse` | 流式问答（SSE 事件流） | SSE 事件流（**不走 ApiResponse 包装**） |

---

## 3. 接口详情

### 3.1 GET /health

健康检查，用于"设置"页的"测试连接"。

**请求**：无参数

**响应 data（HealthResponse）**：
```json
{
  "status": "ok",
  "app": "ragent-py",
  "env": "dev",
  "timestamp": "2026-06-28T08:00:00+00:00",
  "trace_id": "xxx",
  "components": {
    "postgres": { "status": "ok", "latency_ms": 2.5, "error": null },
    "milvus": { "status": "ok", "latency_ms": 5.1, "error": null }
  }
}
```

**前端用法**：
- 仅判断 HTTP 200 且 `code === 0` 即视为连接成功
- `components` 可选展示（如 postgres / milvus 状态）

---

### 3.2 POST /api/v1/knowledge-bases

创建知识库。

**请求体（JSON，KnowledgeBaseCreate）**：
```json
{
  "name": "产品文档库",
  "description": "存放产品手册与说明文档",
  "embedding_model": "text-embedding-v3",
  "embedding_dim": 1024,
  "chunk_strategy": "recursive",
  "chunk_size": 512,
  "chunk_overlap": 64
}
```

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `name` | `string` | 是 | - | 名称（全局唯一，1-128 字符） |
| `description` | `string` | 否 | `null` | 描述（最长 512 字符） |
| `embedding_model` | `string` | 否 | `"text-embedding-v3"` | MVP 固定，前端表单只读 |
| `embedding_dim` | `int` | 否 | `1024` | MVP 固定，前端表单只读 |
| `chunk_strategy` | `string` | 否 | `"recursive"` | 可选 `fixed` / `sentence` / `recursive` |
| `chunk_size` | `int` | 否 | `512` | 范围 (0, 8192] |
| `chunk_overlap` | `int` | 否 | `64` | 必须 < `chunk_size` |

**响应 data（KnowledgeBaseOut）**：
```json
{
  "id": "346549612510711808",
  "name": "产品文档库",
  "description": "存放产品手册与说明文档",
  "collection_name": "kb_346549612510711808",
  "embedding_dim": 1024,
  "embedding_model": "text-embedding-v3",
  "chunk_strategy": "recursive",
  "chunk_size": 512,
  "chunk_overlap": 64,
  "document_count": 0,
  "status": "active",
  "created_at": "2026-06-28T08:00:00",
  "updated_at": "2026-06-28T08:00:00"
}
```

**HTTP 状态**：成功 `201 Created`

**前端校验对齐**：
- 名称必填
- `chunk_overlap` < `chunk_size`（与后端 `field_validator` 一致）
- `chunk_strategy` 必须是 `fixed` / `sentence` / `recursive` 之一

---

### 3.3 GET /api/v1/knowledge-bases

分页列出活跃知识库。

**Query 参数**：
| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `page` | `int` | `1` | 页码（≥1） |
| `page_size` | `int` | `20` | 每页大小（1-100） |

**响应 data（KnowledgeBasePage）**：
```json
{
  "items": [ { "...KnowledgeBaseOut" } ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

---

### 3.4 GET /api/v1/knowledge-bases/{kb_id}

查询单个知识库详情。

**路径参数**：`kb_id`（string）

**响应 data**：`KnowledgeBaseOut`（结构同 3.2）

---

### 3.5 POST /api/v1/documents/upload

上传文档，异步触发摄取 pipeline。

**Content-Type**：`multipart/form-data`

**表单字段**：
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `kb_id` | `string`（Form） | 是 | 目标知识库 ID |
| `file` | `File` | 是 | 文件（txt/md/pdf），大小 ≤ 50MB，内容非空 |

**响应 data（DocumentUploadResponse）**：
```json
{
  "document_id": "346549612510711809",
  "kb_id": "346549612510711808",
  "name": "report.pdf",
  "file_type": "pdf",
  "file_size": 1258291,
  "file_hash": "sha256:...",
  "status": "pending",
  "duplicated": false
}
```

**HTTP 状态**：成功 `201 Created`

**前端约束**：
- 必须用 `FormData` 构造请求体，**不要**手动设置 `Content-Type`（浏览器自动加 boundary）
- 上传后立即返回 `document_id`，状态为 `pending`
- `duplicated === true` 表示 hash 命中已有文档，前端提示"文件已存在，已复用已有文档"
- 文件大小前端先做 50MB 校验，超限直接提示，不发请求

**已知后端校验**：
- 文件 > 50MB → `code: 10202`，message 含大小信息
- 文件内容为空 → `code: 10203`

---

### 3.6 GET /api/v1/documents

分页列出文档（可按知识库过滤）。

**Query 参数**：
| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `kb_id` | `string` | `null` | 按知识库过滤（可选） |
| `page` | `int` | `1` | 页码（≥1） |
| `page_size` | `int` | `20` | 每页大小（1-100） |

**响应 data（DocumentPage）**：
```json
{
  "items": [
    {
      "id": "346549612510711809",
      "kb_id": "346549612510711808",
      "name": "report.pdf",
      "file_type": "pdf",
      "file_size": 1258291,
      "file_hash": "sha256:...",
      "status": "completed",
      "chunk_count": 24,
      "total_tokens": 8200,
      "error_message": null,
      "created_at": "2026-06-28T08:00:00",
      "updated_at": "2026-06-28T08:01:30"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

**DocumentOut 字段说明**：
| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | `string` | 文档 ID |
| `kb_id` | `string` | 所属知识库 ID |
| `name` | `string` | 文件名 |
| `file_type` | `string` | `txt` / `md` / `pdf` |
| `file_size` | `int` | 字节数 |
| `file_hash` | `string` | SHA256 |
| `status` | `string` | 文档状态枚举值（见 3.7） |
| `chunk_count` | `int` | 分块数 |
| `total_tokens` | `int` | token 总数 |
| `error_message` | `string \| null` | 失败原因（status=failed 时有值） |
| `created_at` | `string` | ISO 时间 |
| `updated_at` | `string` | ISO 时间 |

---

### 3.7 GET /api/v1/documents/{document_id}

查询单个文档状态（用于轮询摄取进度）。

**路径参数**：`document_id`（string）

**响应 data**：`DocumentOut`（结构同 3.6 items 元素）

**文档状态机（DocumentStatus）**：
```
pending → parsing → chunking → embedding → indexing → completed
                                                            ↘ failed
```

| 枚举值 | 中文文案 | 是否终态 |
|---|---|---|
| `pending` | 待处理 | 否 |
| `parsing` | 解析中 | 否 |
| `chunking` | 分块中 | 否 |
| `embedding` | 向量化中 | 否 |
| `indexing` | 入库中 | 否 |
| `completed` | 已完成 | 是 |
| `failed` | 失败 | 是 |

**前端轮询策略**：
- 文件管理页每 3 秒调用 `GET /api/v1/documents?kb_id=xxx`
- 若所有文档状态为终态（`completed` / `failed`）→ 停止轮询
- 页面卸载时停止轮询（`onUnmounted`）

---

### 3.8 POST /api/v1/chat/sse

基于知识库的流式问答（SSE 事件流）。

> **重要**：此接口**不走** `ApiResponse` 包装，返回的是 `text/event-stream`。前端必须用 `fetch + ReadableStream` 解析，**禁止**用 `EventSource`（EventSource 仅支持 GET，且无法发送 JSON body）。

**请求**：
- Method：`POST`
- Headers：`Content-Type: application/json`、`Accept: text/event-stream`
- Body（JSON，ChatSseRequest）：

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "kb_id": "346549612510711808",
  "question": "什么是 RAG？",
  "top_k": 5,
  "temperature": 0.0,
  "top_p": 1.0,
  "max_tokens": null
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `session_id` | `string` | 是 | - | 会话 ID（前端生成 UUID，1-64 字符） |
| `kb_id` | `string` | 是 | - | 知识库 ID（1-64 字符） |
| `question` | `string` | 是 | - | 用户问题（非空） |
| `top_k` | `int` | 否 | `5` | 检索 top_k（1-50） |
| `temperature` | `float` | 否 | `0.0` | 采样温度 [0.0, 2.0] |
| `top_p` | `float` | 否 | `1.0` | nucleus sampling (0.0, 1.0] |
| `max_tokens` | `int \| null` | 否 | `null` | 最大输出 token 数 |

**响应**：SSE 事件流，Content-Type `text/event-stream`

**事件格式**（SSE 规范）：
```
event: {type}
data: {json_string}

```

**四类事件**：

| 事件 | event 字段 | data 字段 | 时机 |
|---|---|---|---|
| 开始 | `start` | `{"trace_id": "..."}` | 连接建立后立即发送 |
| 增量 | `delta` | `{"content": "..."}` | LLM 每个 token 到达 |
| 结束 | `done` | `{"trace_id": "...", "finish_reason": "stop"}` | LLM 输出完成 |
| 错误 | `error` | `{"trace_id": "...", "code": 30001, "message": "..."}` | 异常发生时 |

**前端解析要求**：
1. 收到 `start` → 记录 `trace_id`，状态置为"接收中"
2. 收到 `delta` → 把 `content` 追加到当前助手消息
3. 收到 `done` → 状态置为"完成"，停止接收
4. 收到 `error` → 状态置为"错误"，展示中文 `message` + "追踪编号：{trace_id}"

**已知限制**：
- 当前 `done` 事件**不携带引用来源**（citations）。前端 MVP 引用来源区域显示占位文案"本次回答无引用来源"。
- 后端有心跳 `ping=15`（秒），前端解析时应忽略非约定事件（如 `ping`）。

**连接断开处理**：
- 客户端主动断开：调用 `reader.cancel()` 或 `AbortController.abort()`
- 网络异常：fetch reject，前端捕获后提示"连接中断，请重试"

---

## 4. 错误处理方式

### 4.1 统一规则
- 非 SSE 接口：`code !== 0` 视为错误
- 错误展示文案：使用后端返回的 `message`（已为中文友好文案，不含堆栈）
- 错误展示形式：`message.error("{message}，追踪编号：{trace_id}")`
- 网络异常（fetch reject）：`message.error("连接后端失败，请检查 API 地址设置")`

### 4.2 SSE 错误
- 收到 `error` 事件：在助手消息区展示 `message`，并附"追踪编号：{trace_id}"
- fetch 本身失败（无法建立连接）：`message.error("连接后端失败，请检查 API 地址设置")`
- 流中断（未收到 `done` / `error` 即结束）：`message.error("回答中断，请重试")`

### 4.3 HTTP 状态码处理
| HTTP 状态 | 处理 |
|---|---|
| 2xx | 解析 body 的 `code`，`code === 0` 取 `data` |
| 400 | 业务校验错误，展示 `message` |
| 404 | 资源不存在，展示 `message`（如知识库/文档不存在） |
| 422 | 请求体校验失败（FastAPI Pydantic 校验），展示通用文案"请求参数有误"+ 追踪编号 |
| 5xx | 服务异常，展示"服务暂不可用"+ 追踪编号 |

> 后端全局异常处理器已保证 4xx/5xx 也返回 `ApiResponse` 结构（含 `code` / `message` / `trace_id`），前端尽量从 body 解析；body 解析失败时用通用中文文案兜底。

### 4.4 追踪编号展示
- 所有错误提示末尾追加"追踪编号：{trace_id}"
- 若 `trace_id` 为空字符串则不追加
- 用户可复制追踪编号反馈给后端排查

---

## 5. 前端类型定义对齐（types/api.ts）

前端 `web/src/types/api.ts` 应按本文件结构定义 TypeScript 类型，关键映射：

```typescript
// 通用响应
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T | null;
  trace_id: string;
}

// 分页
interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 知识库
interface KnowledgeBaseOut { /* 见 3.2 */ }
interface KnowledgeBaseCreate { /* 见 3.2 */ }

// 文档
interface DocumentOut { /* 见 3.6 */ }
interface DocumentUploadResponse { /* 见 3.5 */ }

// 聊天
interface ChatSseRequest { /* 见 3.8 */ }
```

> 类型定义在 P1.1 创建 `types/api.ts` 时落地，本文件仅作契约说明。

---

## 6. 不在契约范围内（暂缓）

以下接口后端 MVP **未提供**，前端不得调用，也不得自行假设：
- 文档删除接口
- 文档重新摄取接口
- 独立检索接口（`/retrieve`）
- 知识库更新/删除接口
- 对话历史查询接口（`ChatMessagePage` 后端有 schema 但 MVP 未暴露 list 路由）
- 模型供应商管理接口
- 用户认证接口

> 若后续 P1.5 联调发现需要，应先扩展后端再更新本契约，前端不得提前调用未定义接口。
