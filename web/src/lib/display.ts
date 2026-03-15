const displayLabels: Record<string, string> = {
  running: '运行中',
  pausing: '暂停中',
  paused: '已暂停',
  completed: '已完成',
  failed: '失败',
  syncing_repo: '同步仓库',
  collecting_docs: '收集文档',
  indexing: '索引中',
  healthy: '正常',
  degraded: '异常',
  unhealthy: '不可用',
  warning: '告警',
  unknown: '未知',
  ready: '已就绪',
  all: '全部',
  guide: '指南',
  readme: '说明文档',
  reference: '参考文档',
  api_reference: 'API 参考',
  design_spec: '设计规范',
  api_usage: 'API 用法',
  concept: '概念说明',
  general: '通用问答',
  top_dir: '一级目录',
  kit: 'Kit',
  subsystem: '子系统',
  page_kind: '页面类型',
  index_status: '索引状态',
  exclude_readme: '排除 README',
  trace_id: '追踪 ID',
  latency: '耗时',
  intent: '意图',
  used_chunks: '引用片段数',
}

export function displayLabel(value: string) {
  return displayLabels[value] ?? value
}

export function displayLabelsJoin(values?: string[] | null) {
  if (!values?.length) {
    return '加载中...'
  }
  return values.map(displayLabel).join(' / ')
}
