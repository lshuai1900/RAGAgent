/**
 * 前端功能开关（feature flags）
 *
 * 用于在 UI 层隐藏/关闭暂缓或未实现的功能入口。所有开关默认为 false，
 * 后续 Step 1+ 阶段在迁移页面时统一通过引用本文件控制入口的显隐。
 *
 * 本文件不耦合任何后端逻辑，也不影响已实现的真实功能。
 * 禁止把任一开关在 UI 层默认开启为可用入口。
 */

/** 是否显示"规划中"标签页（知识图谱 / 知识导图 / RAG 评估 / 评估基准） */
export const ENABLE_PLANNED_TABS = false

/** 是否启用 Agent 能力（MCP / Skills / SubAgents / 沙盒 / LangGraph 编排） */
export const ENABLE_AGENT_FEATURES = false

/** 是否启用认证相关功能（登录 / JWT / 权限 / 多租户） */
export const ENABLE_AUTH_FEATURES = false

/** 是否启用知识图谱入口 */
export const ENABLE_KNOWLEDGE_GRAPH = false

/** 是否启用 RAG 评估入口 */
export const ENABLE_RAG_EVALUATION = false

/** 是否启用模型路由 / 降级 */
export const ENABLE_MODEL_ROUTING = false

/** 聚合开关对象，便于在组件中按需解构 */
export const featureFlags = {
  enablePlannedTabs: ENABLE_PLANNED_TABS,
  enableAgentFeatures: ENABLE_AGENT_FEATURES,
  enableAuthFeatures: ENABLE_AUTH_FEATURES,
  enableKnowledgeGraph: ENABLE_KNOWLEDGE_GRAPH,
  enableRagEvaluation: ENABLE_RAG_EVALUATION,
  enableModelRouting: ENABLE_MODEL_ROUTING,
} as const
