# DEVELOPMENT_WORKFLOW.md

> Ragent-Py Trae 编码协作流程（强约束）
>
> 本文档定义 Trae（及其他 AI 助手）在本项目编码时必须遵守的流程。

---

## 1. 编码前必读

Trae 每次开始编码前，**必须**先完整阅读以下文件：

1. `AGENTS.md` — 项目定位、当前阶段、技术栈、分层架构、禁止项
2. `docs/PROJECT_SPEC.md` — 项目背景与 MVP 目标
3. `docs/ARCHITECTURE.md` — 分层架构与依赖规则
4. `docs/MVP_PLAN.md` — 当前批次任务范围
5. `docs/DATA_MODEL.md` — 表结构设计
6. `docs/INTERFACES.md` — 抽象接口契约
7. `docs/ACCEPTANCE_CRITERIA.md` — 当前批次验收标准
8. `.trae/rules/` 下与本次修改相关的规则文件

**若未阅读上述文件就动手编码，视为违规。**

---

## 2. 批次推进纪律

### 2.1 严格三批推进

| 批次 | 任务 | 启动条件 |
|---|---|---|
| 第 0 步 | 文档与规则落地 | 终版设计确认 |
| 第一批 | T1-T4 项目骨架与基础设施 | 第 0 步验收通过 |
| 第二批 | T5-T9 文档摄取链路 | 第一批 T1-T4 验收通过 |
| 第三批 | T10-T12、T14-T15、T18 检索与流式问答 | 第二批 T5-T9 验收通过 |

### 2.2 禁止行为

- ❌ **禁止一次性铺开 T1-T18**：只能做当前批次任务
- ❌ **禁止提前实现后续批次功能**：例如第一批不得写 parser/chunker
- ❌ **禁止实现暂缓项**：MCP / 意图识别 / 多路检索 / Rerank 模型 / 熔断 / 限流 / JWT / 复杂 Trace / 管理后台 / Celery 等（详见 AGENTS.md 第 7 节）
- ❌ **禁止跨批次提交**：每批完成后必须验收，验收通过才能进入下一批

### 2.3 当前批次确认

每次编码开始前，Trae 必须先确认：
- 当前处于哪个批次？
- 本次要完成哪些任务（T 编号）？
- 这些任务是否属于当前批次范围？

若用户要求实现超出当前批次范围的功能，Trae 应**主动拒绝并提示**当前批次范围。

---

## 3. 修改前输出（设计阶段）

每次代码修改前，Trae **必须**先输出以下内容，等用户确认后再动手：

### 3.1 涉及文件清单
- 列出本次将新增/修改/删除的文件路径
- 标注每个文件属于哪一层（api / service / domain / persistence / infra_ai / rag / ingestion / schemas / framework）

### 3.2 设计理由
- 为什么这样设计？（与 ARCHITECTURE.md / INTERFACES.md 对应）
- 涉及哪些抽象接口？（列出 base 接口与实现类）
- 依赖方向是否符合规则？（对照 ARCHITECTURE.md 第 3 节）

### 3.3 测试方式
- 单元测试覆盖哪些场景？
- 集成测试如何验证？
- LLM/Milvus/DB 如何 Mock？

### 3.4 验收对照
- 对照 ACCEPTANCE_CRITERIA.md，本次修改对应哪些验收项？

---

## 4. 修改后输出（验收阶段）

每次代码修改完成后，Trae **必须**输出以下内容：

### 4.1 新增/修改文件清单
- 完整文件路径列表
- 每个文件的简要说明（1 句话）

### 4.2 运行命令
- 依赖安装命令（如 `uv sync`）
- lint 命令（`make lint` 或 `uv run ruff check`）
- typecheck 命令（`make typecheck` 或 `uv run mypy src`）
- 测试命令（`make test` 或 `uv run pytest`）
- 迁移命令（如涉及 DB：`uv run alembic upgrade head`）
- 启动命令（`make dev` 或 `uv run uvicorn ragent.main:app`）

### 4.3 验收结果
- lint 是否零警告？
- typecheck 是否零错误？
- 测试是否全部通过？
- 对照 ACCEPTANCE_CRITERIA.md，本次完成的验收项打勾
- 若有未完成项，明确列出原因与后续计划

---

## 5. 编码规范检查清单

每次提交前，Trae 必须自检以下项（对照 `.trae/rules/`）：

### 5.1 分层架构
- [ ] api 只调 service，未直接调 repository/infra_ai/rag/ingestion
- [ ] domain 未 import schemas/persistence/infra_ai/rag/ingestion/api/framework
- [ ] schemas 顶层独立，未被 domain 依赖
- [ ] ORM Model 只在 persistence/models/
- [ ] base 接口只依赖 domain，未依赖 persistence
- [ ] framework 未 import 任何业务层

### 5.2 异步规范
- [ ] 所有 IO 操作为 async
- [ ] 无同步阻塞调用（DB/HTTP/Milvus）
- [ ] 无 time.sleep（用 asyncio.sleep）
- [ ] 并行用 asyncio.gather
- [ ] 并发控制用 Semaphore
- [ ] trace_id 用 contextvars 透传

### 5.3 数据规范
- [ ] 表名 t_ 前缀
- [ ] 主键雪花 ID
- [ ] created_at/updated_at 自动填充
- [ ] ORM Model 与 Pydantic Schema 分离
- [ ] 向量入 Milvus，元数据入 PG

### 5.4 异常规范
- [ ] 三级异常（Biz/Sys/Infra）
- [ ] 错误码段位正确（1xxxx/2xxxx/3xxxx）
- [ ] 全局异常拦截器包装 ApiResponse
- [ ] 未捕获异常不泄露堆栈

### 5.5 MVP 范围
- [ ] 未实现暂缓项
- [ ] 未跨批次实现
- [ ] TraceSpan 仅预留（MVP 不写 Span）
- [ ] 异步摄取用 BackgroundTasks（未引入 Celery）
- [ ] Memory 仅 load/append（无 summarize）
- [ ] Rerank 仅 Identity（无模型调用）

---

## 6. 异常处理流程

### 6.1 遇到不确定的设计决策
- **不要**自行臆断
- **不要**绕过规则
- 主动向用户提问，提供 2-3 个选项与权衡

### 6.2 发现规则冲突
- 停止编码
- 列出冲突点（哪两条规则冲突）
- 向用户请示如何处理

### 6.3 发现需要实现暂缓项
- **立即停止**
- 向用户说明该功能属于暂缓项
- 提示当前批次范围
- 等待用户明确指示（是否调整批次计划）

---

## 7. 提交规范

每批完成后按 Conventional Commits 提交：

```
feat(rag): 实现向量检索通道
fix(ingestion): 修复 PDF 分页元信息丢失
docs(readme): 更新 MVP 接口说明
optimize(infra-ai): LLM 流式首包探测
chore(persistence): 补充 TraceSpan 预留表迁移
test(rag): 补充检索器单元测试
```

scope 用模块名：rag / ingestion / infra-ai / persistence / service / schemas / framework / api。

**禁止**在没有用户明确指示时自动提交。

---

## 8. 文档同步

当代码修改影响以下内容时，必须同步更新对应文档：

| 修改内容 | 需同步的文档 |
|---|---|
| 新增/修改表结构 | docs/DATA_MODEL.md |
| 新增/修改抽象接口 | docs/INTERFACES.md |
| 调整分层或依赖 | docs/ARCHITECTURE.md + AGENTS.md |
| 调整批次或任务 | docs/MVP_PLAN.md + docs/ACCEPTANCE_CRITERIA.md |
| 新增规则或约束 | .trae/rules/ 对应文件 + AGENTS.md |
