import type { BuildRunSummary, ServiceStatus, StatsResponse } from '@/lib/types'

export const navigationItems = [
  { to: '/', label: '工作台', icon: 'layout-dashboard' },
  { to: '/builds', label: '构建中心', icon: 'workflow' },
  { to: '/lab', label: '接口实验室', icon: 'flask-conical' },
  { to: '/chat', label: '智能问答', icon: 'messages-square' },
  { to: '/services', label: '服务状态', icon: 'activity' },
  { to: '/integrations', label: '集成指南', icon: 'plug-zap' },
  { to: '/explorer', label: '索引浏览', icon: 'files' },
] as const

export const apiLabTemplates = {
  retrieve: `{
  "query": "如何创建 UIAbility 组件？",
  "top_k": 5,
  "filters": {
    "top_dir": "application-dev",
    "exclude_readme": true
  }
}`,
  query: `{
  "query": "router.pushUrl 方法如何使用？",
  "top_k": 6,
  "filters": {
    "top_dir": "application-dev",
    "exclude_readme": true
  }
}`,
}

export const chatPromptSuggestions = [
  '如何创建 UIAbility 组件？',
  'ArkUI 中 router.pushUrl 的常见用法是什么？',
  'OpenHarmony 中如何理解设计规范文档？',
]

export const fallbackRun: BuildRunSummary = {
  id: '本地预览',
  mode: 'sync_incremental',
  status: 'paused',
  stage: 'paused',
  started_at: '2026-03-14T10:00:00',
  updated_at: '2026-03-14T10:05:00',
  processed_docs: 0,
  total_docs: 0,
  indexed_docs: 0,
  reindexed_docs: 0,
  skipped_docs: 0,
  failed_docs: 0,
  current_path: '',
  can_pause: false,
  can_resume: false,
}

export const fallbackServices: ServiceStatus[] = [
  {
    name: 'API',
    status: 'unknown',
    host: '127.0.0.1',
    port: 8000,
    details: '等待连接本地 FastAPI 服务',
  },
  {
    name: 'Qdrant',
    status: 'unknown',
    host: '127.0.0.1',
    port: 6333,
    details: '等待探测向量服务端口',
  },
  {
    name: 'SQLite',
    status: 'unknown',
    host: 'local',
    port: 0,
    details: '等待探测 metadata.db 文件',
  },
]

export const fallbackStats: StatsResponse = {
  total_documents: 0,
  by_top_dir: {},
  by_kit: {},
  by_page_kind: {},
  document_types: {
    api_reference: 0,
    guide: 0,
    design_spec: 0,
  },
}

export const mcpConfigSnippet = `{
  "mcpServers": {
    "openharmony-docs-rag": {
      "command": "/absolute/path/to/openharmony-docs-rag/venv/bin/python",
      "args": ["-m", "rag_mcp.stdio_server"],
      "cwd": "/absolute/path/to/openharmony-docs-rag",
      "env": {
        "OPENHARMONY_RAG_API_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}`

export const skillSnippet = `from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill

skill = OpenHarmonyDocsRAGSkill(api_base_url="http://127.0.0.1:8000")
result = await skill.ask_question("如何创建 UIAbility 组件？")
print(skill.format_answer(result))`

export const envGuideGroups = [
  {
    title: '核心模型配置',
    description: '优先填写 LLM 和 Embedding 的 API Key、Base URL 与模型名。',
  },
  {
    title: '检索与重排',
    description: '通过 RERANK_ENABLED、RERANK_MODEL、RETRIEVAL_TOP_K 等参数调节召回策略。',
  },
  {
    title: '文档与索引',
    description: 'DOCS_LOCAL_PATH、DOCS_INCLUDE_DIRS、CHUNK_TARGET_SIZE 会影响建库行为。',
  },
]
