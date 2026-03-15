/**
 * Console page components for the OpenHarmony Docs RAG local operations workspace.
 */
import { useEffect, useEffectEvent, useMemo, useState } from 'react'
import {
  ArrowRight,
  Bot,
  Play,
  RefreshCw,
  Save,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
} from 'recharts'
import { Link } from 'react-router-dom'

import { runQuery, runRetrieve } from '@/lib/api'
import {
  apiLabTemplates,
  chatPromptSuggestions,
  envGuideGroups,
  mcpConfigSnippet,
  skillSnippet,
} from '@/lib/console-data'
import { displayLabel, displayLabelsJoin } from '@/lib/display'
import type {
  BuildMode,
  BuildRunSummary,
  CapabilitiesResponse,
  Citation,
  ConsoleLogEntry,
  DocumentDetail,
  DocumentRecord,
  DocumentsResponse,
  EnvPayload,
  QueryResponse,
  ServiceStatus,
  StatsResponse,
} from '@/lib/types'
import { CodeBlock } from '@/components/code-block'
import { StatusBadge } from '@/components/status-badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Progress } from '@/components/ui/progress'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

function percent(processed: number, total: number) {
  if (!total) {
    return 0
  }
  return Math.min(100, Math.round((processed / total) * 100))
}

function formatDate(value?: string | null) {
  if (!value) {
    return '未记录'
  }
  return new Date(value).toLocaleString('zh-CN')
}

function statusTone(value: string) {
  if (['healthy', 'completed', 'ready'].includes(value)) {
    return 'healthy' as const
  }
  if (['running', 'indexing'].includes(value)) {
    return 'running' as const
  }
  if (['paused', 'pausing'].includes(value)) {
    return 'paused' as const
  }
  if (['degraded', 'warning'].includes(value)) {
    return 'warning' as const
  }
  if (['failed', 'error', 'unhealthy'].includes(value)) {
    return 'danger' as const
  }
  return 'unknown' as const
}

function summaryCards(run: BuildRunSummary, stats: StatsResponse) {
  return [
    {
      label: '文档总量',
      value: stats.total_documents.toLocaleString(),
      hint: '当前索引库中的文档数',
    },
    {
      label: '本轮进度',
      value: `${run.processed_docs}/${run.total_docs || '—'}`,
      hint: '已处理 / 总文档数',
    },
    {
      label: '失败文档',
      value: String(run.failed_docs),
      hint: '需在索引浏览中排查',
    },
    {
      label: '已跳过',
      value: String(run.skipped_docs),
      hint: '恢复时会继续沿用已就绪文档',
    },
  ]
}

function topBarData(stats: Record<string, number>) {
  return Object.entries(stats)
    .slice(0, 6)
    .map(([label, value]) => ({ label: displayLabel(label), value }))
}

export function WorkspacePage({
  latestRun,
  services,
  stats,
  onStartBuild,
  onPause,
  onResume,
}: {
  latestRun: BuildRunSummary
  services: ServiceStatus[]
  stats: StatsResponse
  onStartBuild: (mode: BuildMode) => Promise<unknown>
  onPause: (runId: string) => Promise<unknown>
  onResume: (runId: string) => Promise<unknown>
}) {
  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
        <Card className="overflow-hidden border-border/70 bg-[linear-gradient(135deg,rgba(5,15,31,0.98),rgba(14,32,57,0.94))] text-white shadow-[0_30px_80px_rgba(1,8,20,0.4)]">
          <CardContent className="relative overflow-hidden p-8">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(32,197,255,0.22),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(77,255,180,0.18),transparent_28%)]" />
            <div className="relative space-y-6">
              <Badge className="rounded-full border border-white/15 bg-white/10 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-white/70">
                工业控制台
              </Badge>
              <div className="max-w-2xl space-y-3">
                <h2 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">
                  一条工作流，从文档同步到带引用回答验证。
                </h2>
                <p className="max-w-xl text-sm leading-6 text-slate-200/80">
                  默认主动作会先同步 OpenHarmony 文档仓库，再执行增量建库。
                  过程中支持安全暂停，恢复后继续增量更新。
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Button
                  className="rounded-2xl bg-cyan-400 px-5 text-slate-950 hover:bg-cyan-300"
                  onClick={() => void onStartBuild('sync_incremental')}
                >
                  <Play className="size-4" />
                  同步文档并增量构建
                </Button>
                <Button
                  variant="secondary"
                  className="rounded-2xl border border-white/10 bg-white/10 text-white hover:bg-white/15"
                  onClick={() =>
                    latestRun.can_pause
                      ? void onPause(latestRun.id)
                      : latestRun.can_resume
                        ? void onResume(latestRun.id)
                        : undefined
                  }
                >
                  {latestRun.can_pause ? '安全暂停' : '继续增量恢复'}
                </Button>
                <Button
                  asChild
                  variant="ghost"
                  className="rounded-2xl border border-white/10 text-white hover:bg-white/10"
                >
                  <Link to="/lab">
                    前往接口实验室
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/80 backdrop-blur-xl">
          <CardHeader className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>当前任务</CardTitle>
                <CardDescription>显示最新一次构建任务的实时状态。</CardDescription>
              </div>
              <StatusBadge
                label={displayLabel(latestRun.status)}
                tone={statusTone(latestRun.status)}
                pulse={latestRun.status === 'running'}
              />
            </div>
            <Progress value={percent(latestRun.processed_docs, latestRun.total_docs)} />
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <InfoRow label="阶段" value={displayLabel(latestRun.stage)} />
            <InfoRow label="当前文件" value={latestRun.current_path || '等待任务启动'} />
            <InfoRow label="启动时间" value={formatDate(latestRun.started_at)} />
            <InfoRow label="更新时间" value={formatDate(latestRun.updated_at)} />
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards(latestRun, stats).map((item) => (
          <Card key={item.label} className="border-border/70 bg-card/75">
            <CardHeader className="pb-2">
              <CardDescription>{item.label}</CardDescription>
              <CardTitle className="text-3xl">{item.value}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{item.hint}</CardContent>
          </Card>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="border-border/70 bg-card/75">
          <CardHeader>
            <CardTitle>服务与端口</CardTitle>
            <CardDescription>确认本地依赖是否已就绪，再开始构建或问答。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            {services.map((service) => (
              <div
                key={service.name}
                className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/60 px-4 py-3"
              >
                <div>
                  <p className="font-medium">{service.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {service.host}:{service.port}
                  </p>
                </div>
                <StatusBadge label={service.status} tone={statusTone(service.status)} />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/75">
          <CardHeader>
            <CardTitle>快捷入口</CardTitle>
            <CardDescription>直接跳到调试、问答和集成配置。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <QuickLinkCard
              title="接口实验室"
              description="适合调试原始请求与响应，支持默认示例值。"
              to="/lab"
            />
            <QuickLinkCard
              title="智能问答"
              description="展示引用、追踪 ID、耗时与意图识别。"
              to="/chat"
            />
            <QuickLinkCard
              title="Skill / MCP 指南"
              description="查看接入代码片段和 Docker 部署后的连接方式。"
              to="/integrations"
            />
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

/**
 * Surface all build workflow controls and log output needed by operators and E2E automation.
 */
export function BuildCenterPage({
  latestRun,
  logs,
  onStartBuild,
  onPause,
  onResume,
}: {
  latestRun: BuildRunSummary
  logs: ConsoleLogEntry[]
  onStartBuild: (mode: BuildMode) => Promise<unknown>
  onPause: (runId: string) => Promise<unknown>
  onResume: (runId: string) => Promise<unknown>
}) {
  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="border-border/70 bg-card/80">
          <CardHeader className="space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>构建任务控制台</CardTitle>
                <CardDescription>
                  默认模式会同步仓库并执行增量构建。全量重建是危险操作。
                </CardDescription>
              </div>
              <div data-testid="build-status">
                <StatusBadge
                  label={displayLabel(latestRun.status)}
                  tone={statusTone(latestRun.status)}
                  pulse={latestRun.status === 'running'}
                />
              </div>
            </div>
            <Progress value={percent(latestRun.processed_docs, latestRun.total_docs)} />
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <ActionButton
                label="同步并增量构建"
                testId="build-start-sync"
                onClick={() => void onStartBuild('sync_incremental')}
              />
              <ActionButton
                label="仅增量构建"
                testId="build-start-incremental"
                onClick={() => void onStartBuild('incremental')}
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <ActionButton
                label={latestRun.can_pause ? '安全暂停' : '继续增量恢复'}
                testId="build-pause-resume"
                onClick={() =>
                  latestRun.can_pause
                    ? void onPause(latestRun.id)
                    : latestRun.can_resume
                      ? void onResume(latestRun.id)
                      : undefined
                }
                disabled={!latestRun.can_pause && !latestRun.can_resume}
              />
              <Dialog>
                <DialogTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full rounded-2xl border-rose-500/40 text-rose-200 hover:bg-rose-500/10"
                    data-testid="build-full-rebuild"
                  >
                    全量重建
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>确认执行全量重建？</DialogTitle>
                    <DialogDescription>
                      这会清空 SQLite 和 Qdrant 中现有索引，再重新处理全部文档。
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button
                      className="rounded-xl bg-rose-500 text-white hover:bg-rose-400"
                      data-testid="build-full-rebuild-confirm"
                      onClick={() => void onStartBuild('full_rebuild')}
                    >
                      确认重建
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
            <div className="rounded-2xl border border-border/70 bg-background/55 p-4 text-sm">
              <div className="grid gap-2 sm:grid-cols-2">
                <InfoRow label="阶段" value={displayLabel(latestRun.stage)} />
                <InfoRow label="当前文件" value={latestRun.current_path || '等待任务启动'} />
                <InfoRow label="已处理" value={String(latestRun.processed_docs)} />
                <InfoRow label="失败数" value={String(latestRun.failed_docs)} />
                <InfoRow
                  label="跳过数"
                  value={String(latestRun.skipped_docs)}
                  testId="build-stat-skipped"
                />
                <InfoRow label="最近更新" value={formatDate(latestRun.updated_at)} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-[linear-gradient(180deg,rgba(2,10,26,0.94),rgba(7,18,34,0.98))] text-slate-100 shadow-[0_24px_70px_rgba(1,8,20,0.38)]">
          <CardHeader>
            <CardTitle className="text-slate-50">过程日志</CardTitle>
            <CardDescription className="text-slate-300/80">
              后端 SSE 事件会实时写入中文日志流。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea
              className="h-[420px] rounded-2xl border border-white/10 bg-black/30 p-4"
              data-testid="build-log-panel"
            >
              <div className="space-y-3 font-mono text-xs">
                {logs.length ? (
                  logs.map((log) => (
                    <div
                      key={log.seq}
                      className="rounded-xl border border-white/5 bg-white/5 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-3 text-[10px] uppercase tracking-[0.2em] text-slate-400">
                        <span>{log.type}</span>
                        <span>{formatDate(log.timestamp)}</span>
                      </div>
                      <p className="mt-2 whitespace-pre-wrap text-cyan-50">{log.message}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-slate-400">任务启动后将在这里显示中文过程日志。</p>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

export function ApiLabPage() {
  const [mode, setMode] = useState<'retrieve' | 'query'>('retrieve')
  const [requestText, setRequestText] = useState(apiLabTemplates.retrieve)
  const [responseText, setResponseText] = useState('')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      const payload = JSON.parse(requestText)
      const response =
        mode === 'retrieve' ? await runRetrieve(payload) : await runQuery(payload)
      setResponseText(JSON.stringify(response, null, 2))
    } catch (currentError) {
      setError(
        currentError instanceof Error ? currentError.message : '执行请求失败'
      )
    } finally {
      setRunning(false)
    }
  }

  const handleCopy = async (value: string) => {
    await navigator.clipboard.writeText(value)
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>接口实验室</CardTitle>
          <CardDescription>适合调试原始请求与响应，并观察结构化 JSON 结果。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Tabs
            value={mode}
            onValueChange={(nextValue) => {
              const nextMode = nextValue as 'retrieve' | 'query'
              setMode(nextMode)
              setRequestText(apiLabTemplates[nextMode])
              setResponseText('')
              setError(null)
            }}
          >
            <TabsList className="grid w-full grid-cols-2 rounded-2xl">
              <TabsTrigger value="retrieve">/retrieve</TabsTrigger>
              <TabsTrigger value="query">/query</TabsTrigger>
            </TabsList>
            <TabsContent value="retrieve" className="mt-4 space-y-4">
              <LabPanel
                description="仅执行检索，不生成回答，适合验证过滤条件和返回条数。"
                requestText={requestText}
                responseText={responseText}
                error={error}
                running={running}
                onChange={setRequestText}
                onRun={handleRun}
                onCopy={handleCopy}
              />
            </TabsContent>
            <TabsContent value="query" className="mt-4 space-y-4">
              <LabPanel
                description="执行完整 RAG 问答，返回回答、引用、追踪 ID 和耗时。"
                requestText={requestText}
                responseText={responseText}
                error={error}
                running={running}
                onChange={setRequestText}
                onRun={handleRun}
                onCopy={handleCopy}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}

function LabPanel({
  description,
  requestText,
  responseText,
  error,
  running,
  onChange,
  onRun,
  onCopy,
}: {
  description: string
  requestText: string
  responseText: string
  error: string | null
  running: boolean
  onChange: (value: string) => void
  onRun: () => void
  onCopy: (value: string) => Promise<void>
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <Card className="border-border/70 bg-background/65">
        <CardHeader>
          <CardTitle className="text-lg">请求体</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            className="min-h-[360px] rounded-2xl font-mono text-xs"
            value={requestText}
            onChange={(event) => onChange(event.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <Button className="rounded-2xl" onClick={onRun} disabled={running}>
              <Play className="size-4" />
              {running ? '执行中...' : '执行请求'}
            </Button>
            <Button
              variant="outline"
              className="rounded-2xl"
              onClick={() => void onCopy(requestText)}
            >
              复制请求体
            </Button>
          </div>
          {error ? (
            <p className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-border/70 bg-[linear-gradient(180deg,rgba(2,10,26,0.92),rgba(5,12,24,0.98))] text-white">
        <CardHeader>
          <CardTitle className="text-lg text-white">响应结果</CardTitle>
          <CardDescription className="text-slate-300/80">
            当前响应支持格式化展示和一键复制。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ScrollArea className="h-[360px] rounded-2xl border border-white/10 bg-black/20 p-4">
            <pre className="whitespace-pre-wrap font-mono text-xs leading-6 text-cyan-50">
              {responseText || '尚未执行请求。'}
            </pre>
          </ScrollArea>
          <Button
            variant="secondary"
            className="rounded-2xl bg-white/10 text-white hover:bg-white/15"
            onClick={() => void onCopy(responseText)}
            disabled={!responseText}
          >
            复制响应 JSON
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export function ChatPage() {
  const [query, setQuery] = useState(chatPromptSuggestions[0])
  const [topDir, setTopDir] = useState('application-dev')
  const [excludeReadme, setExcludeReadme] = useState(true)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<QueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true)
    setError(null)
    try {
      setResult(
        await runQuery({
          query,
          top_k: 6,
          filters: {
            top_dir: topDir,
            exclude_readme: excludeReadme,
          },
        })
      )
    } catch (currentError) {
      setError(
        currentError instanceof Error ? currentError.message : '问答请求失败'
      )
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>智能问答</CardTitle>
          <CardDescription>
            默认展示中文示例问题，并返回引用、追踪 ID、耗时和意图识别结果。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-4">
              <Textarea
                className="min-h-40 rounded-2xl text-sm"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                {chatPromptSuggestions.map((prompt) => (
                  <Button
                    key={prompt}
                    type="button"
                    variant="outline"
                    className="rounded-full"
                    onClick={() => setQuery(prompt)}
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <p className="text-sm font-medium">一级目录</p>
                  <Select value={topDir} onValueChange={setTopDir}>
                    <SelectTrigger className="rounded-2xl">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="application-dev">application-dev</SelectItem>
                      <SelectItem value="design">design</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/50 px-4 py-3">
                  <div>
                    <p className="text-sm font-medium">排除 README</p>
                    <p className="text-xs text-muted-foreground">聚焦更稳定的文档块</p>
                  </div>
                  <Switch checked={excludeReadme} onCheckedChange={setExcludeReadme} />
                </div>
              </div>
              <Button className="rounded-2xl" onClick={() => void handleRun()} disabled={running}>
                <Bot className="size-4" />
                {running ? '生成中...' : '获取带引用回答'}
              </Button>
            </div>

            <Card className="border-border/70 bg-background/55">
              <CardHeader>
                <CardTitle className="text-lg">响应摘要</CardTitle>
                <CardDescription>会展示回答、引用、追踪 ID 和耗时。</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <InfoRow label="追踪 ID" value={result?.trace_id ?? '等待请求'} />
                <InfoRow
                  label="耗时"
                  value={result ? `${result.latency_ms} ms` : '等待请求'}
                />
                <InfoRow
                  label="意图"
                  value={
                    result
                      ? `${displayLabel(result.intent.type)} (${result.intent.confidence.toFixed(2)})`
                      : '等待请求'
                  }
                />
                <InfoRow
                  label="引用片段数"
                  value={result ? String(result.used_chunks) : '等待请求'}
                />
              </CardContent>
            </Card>
          </div>

          {error ? (
            <p className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </p>
          ) : null}

          <Card className="border-border/70 bg-card/75">
            <CardHeader>
              <CardTitle className="text-lg">回答与引用</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-2xl border border-border/70 bg-background/55 p-4 text-sm leading-7">
                {result?.answer ?? '提交问题后，这里会显示带引用回答。'}
              </div>
              <div className="grid gap-3">
                {result?.citations.length ? (
                  result.citations.map((citation) => (
                    <CitationCard key={`${citation.path}-${citation.heading_path}`} citation={citation} />
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">暂无引用。</p>
                )}
              </div>
            </CardContent>
          </Card>
        </CardContent>
      </Card>
    </div>
  )
}

function CitationCard({ citation }: { citation: Citation }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-background/55 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className="rounded-full border border-cyan-500/20 bg-cyan-500/10 text-cyan-200">
          引用
        </Badge>
        <p className="font-medium">{citation.title ?? citation.path}</p>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{citation.heading_path}</p>
      <p className="mt-3 text-sm leading-6">{citation.snippet}</p>
      <a
        className="mt-3 inline-flex text-sm text-cyan-300 hover:text-cyan-200"
        href={citation.source_url}
        target="_blank"
        rel="noreferrer"
      >
        打开源文档
      </a>
    </div>
  )
}

/**
 * Renders service health, capability summary, and deploy/app.env editing with validation guidance.
 */
export function ServicesPage({
  services,
  capabilities,
  envPayload,
  onRefreshServices,
  onSaveEnv,
}: {
  services: ServiceStatus[]
  capabilities: CapabilitiesResponse | null
  envPayload: EnvPayload
  onRefreshServices: () => Promise<unknown>
  onSaveEnv: (raw: string) => Promise<unknown>
}) {
  const [draft, setDraft] = useState(envPayload.raw)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!dirty) {
      setDraft(envPayload.raw)
    }
  }, [dirty, envPayload.raw])

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-border/70 bg-card/80">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>服务状态</CardTitle>
              <CardDescription>展示 API、Qdrant、SQLite 与端口探测结果。</CardDescription>
            </div>
            <Button variant="outline" className="rounded-2xl" onClick={() => void onRefreshServices()}>
              <RefreshCw className="size-4" />
              刷新
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {services.map((service) => (
              <div
                key={service.name}
                className="rounded-2xl border border-border/70 bg-background/60 p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{service.name}</p>
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      {service.host}:{service.port}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">{service.details}</p>
                  </div>
                  <StatusBadge label={displayLabel(service.status)} tone={statusTone(service.status)} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>能力摘要</CardTitle>
          <CardDescription>帮助确认当前模型、意图分类与过滤支持范围。</CardDescription>
        </CardHeader>
          <CardContent className="grid gap-4">
            <InfoRow label="Embedding 模型" value={capabilities?.embedding_model ?? '加载中...'} />
            <InfoRow label="Chat 模型" value={capabilities?.chat_model ?? '加载中...'} />
            <InfoRow
              label="支持意图"
              value={displayLabelsJoin(capabilities?.supported_intents)}
            />
            <InfoRow
              label="支持过滤"
              value={displayLabelsJoin(capabilities?.supported_filters)}
            />
          </CardContent>
        </Card>
      </section>

        <Card className="border-border/70 bg-card/80">
          <CardHeader>
          <CardTitle>deploy/app.env 配置</CardTitle>
          <CardDescription>当前编辑的是 Docker 部署运行时配置文件 deploy/app.env。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
          <div className="space-y-3">
            {envGuideGroups.map((group) => (
              <div
                key={group.title}
                className="rounded-2xl border border-border/70 bg-background/55 p-4"
              >
                <p className="font-medium">{group.title}</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {group.description}
                </p>
              </div>
            ))}
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm text-amber-900 dark:text-amber-100">
              <p className="font-medium">校验提示</p>
              <ul className="mt-2 space-y-1 text-amber-800/90 dark:text-amber-50/85">
                {envPayload.warnings.length ? (
                  envPayload.warnings.map((warning) => <li key={warning}>• {warning}</li>)
                ) : (
                  <li>• 当前未检测到核心字段缺失。</li>
                )}
              </ul>
            </div>
          </div>
          <div className="space-y-3">
            <p className="text-sm leading-6 text-muted-foreground">
              保存后重新执行 <code>docker compose --env-file deploy/app.env up -d</code>，即可让新配置生效。
            </p>
            <Textarea
              className="min-h-[420px] rounded-3xl font-mono text-xs"
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value)
                setDirty(true)
              }}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button
                className="rounded-2xl"
                onClick={async () => {
                  await onSaveEnv(draft)
                  setDirty(false)
                }}
              >
                <Save className="size-4" />
                保存 deploy/app.env
              </Button>
              <Badge className="rounded-full border border-border/70 bg-background/55 text-muted-foreground">
                最近修改：{envPayload.last_modified ? formatDate(envPayload.last_modified) : '未记录'}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function IntegrationsPage() {
  return (
    <div className="space-y-6">
      <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>集成指南</CardTitle>
          <CardDescription>用中文解释接入步骤，配置片段保留原始代码格式。</CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="space-y-3">
            <AccordionItem value="skill" className="rounded-2xl border border-border/70 px-4">
              <AccordionTrigger>如何配置 Skill 封装</AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <p className="text-sm leading-6 text-muted-foreground">
                  先启动本地 RAG API，再通过 Python 封装直接发起问答或检索。
                </p>
                <CodeBlock title="Skill 封装示例" code={skillSnippet} />
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="mcp" className="rounded-2xl border border-border/70 px-4">
              <AccordionTrigger>如何配置 MCP 服务</AccordionTrigger>
              <AccordionContent className="space-y-4 pb-4">
                <p className="text-sm leading-6 text-muted-foreground">
                  MCP 服务使用 stdio 方式运行，并通过 OPENHARMONY_RAG_API_BASE_URL 指向本地 API。
                </p>
                <CodeBlock title="MCP 客户端配置" code={mcpConfigSnippet} />
              </AccordionContent>
            </AccordionItem>
            <AccordionItem value="checklist" className="rounded-2xl border border-border/70 px-4">
              <AccordionTrigger>接入前检查清单</AccordionTrigger>
              <AccordionContent className="pb-4">
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• 确认 API 服务已启动并监听 8000 端口。</li>
                  <li>• 构建索引前，先补齐 deploy/app.env 中的 LLM/Embedding 配置。</li>
                  <li>• 如果使用 MCP，避免在 stdio 服务中向 stdout 打日志。</li>
                  <li>• 如果恢复增量构建，已就绪文档会被跳过，只重试未完成内容。</li>
                </ul>
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>
    </div>
  )
}

/**
 * Expose read-only index statistics and document metadata browsing for operational verification.
 */
export function IndexExplorerPage({
  stats,
  documents,
  documentDetail,
  documentDetailLoading = false,
  topDirOptions,
  pageKindOptions,
  onRefreshDocuments,
  onLoadDocumentDetail,
}: {
  stats: StatsResponse
  documents: DocumentsResponse
  documentDetail?: DocumentDetail | null
  documentDetailLoading?: boolean
  topDirOptions: string[]
  pageKindOptions: string[]
  onRefreshDocuments: (params?: {
    indexStatus?: string
    topDir?: string
    pageKind?: string
  }) => Promise<unknown>
  onLoadDocumentDetail?: (docId: string) => Promise<unknown>
}) {
  const [indexStatus, setIndexStatus] = useState('all')
  const [topDir, setTopDir] = useState('all')
  const [pageKind, setPageKind] = useState('all')
  const [selectedDocument, setSelectedDocument] = useState<DocumentRecord | null>(null)

  const topDirChart = useMemo(() => topBarData(stats.by_top_dir), [stats.by_top_dir])
  const pageKindChart = useMemo(
    () => topBarData(stats.by_page_kind),
    [stats.by_page_kind]
  )
  const refreshDocumentsEvent = useEffectEvent(onRefreshDocuments)
  const selectedDetail =
    documentDetail && selectedDocument && documentDetail.doc_id === selectedDocument.doc_id
      ? documentDetail
      : selectedDocument

  useEffect(() => {
    void refreshDocumentsEvent({ indexStatus, topDir, pageKind })
  }, [indexStatus, topDir, pageKind])

  return (
    <div className="space-y-6">
      <section className="grid gap-6 xl:grid-cols-2">
        <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>目录分布</CardTitle>
          <CardDescription>展示一级目录中文档数分布。</CardDescription>
        </CardHeader>
          <CardContent>
            <ChartContainer
              className="h-72"
              config={{
                value: {
                  label: '文档数',
                  theme: {
                    light: 'hsl(191 95% 40%)',
                    dark: 'hsl(188 100% 70%)',
                  },
                },
              }}
            >
              <BarChart data={topDirChart}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="value" radius={12} fill="var(--color-value)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card className="border-border/70 bg-card/80">
          <CardHeader>
            <CardTitle>页面类型分布</CardTitle>
            <CardDescription>指南、API 参考、设计规范三类文档的数量变化。</CardDescription>
          </CardHeader>
          <CardContent>
            <ChartContainer
              className="h-72"
              config={{
                value: {
                  label: '文档数',
                  theme: {
                    light: 'hsl(154 69% 45%)',
                    dark: 'hsl(156 85% 66%)',
                  },
                },
              }}
            >
              <BarChart data={pageKindChart}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="label" tickLine={false} axisLine={false} />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="value" radius={12} fill="var(--color-value)" />
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </section>

      <Card className="border-border/70 bg-card/80">
        <CardHeader>
          <CardTitle>索引文档列表</CardTitle>
          <CardDescription>支持按索引状态、一级目录、页面类型组合过滤。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <FilterSelect
              label="index_status"
              value={indexStatus}
              options={['all', 'ready', 'indexing', 'failed']}
              onChange={setIndexStatus}
            />
            <FilterSelect
              label="top_dir"
              value={topDir}
              options={topDirOptions}
              onChange={setTopDir}
            />
            <FilterSelect
              label="page_kind"
              value={pageKind}
              options={pageKindOptions}
              onChange={setPageKind}
            />
          </div>
          <div className="rounded-3xl border border-border/70 bg-background/55">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>路径</TableHead>
                  <TableHead>Kit</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>错误</TableHead>
                  <TableHead className="text-right">详情</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.documents.length ? (
                  documents.documents.map((document) => (
                    <TableRow key={document.doc_id}>
                      <TableCell className="font-mono text-xs">{document.path}</TableCell>
                      <TableCell>{document.kit ?? '—'}</TableCell>
                      <TableCell>{document.page_kind ? displayLabel(document.page_kind) : '—'}</TableCell>
                      <TableCell>
                        <StatusBadge
                          label={displayLabel(document.index_status ?? 'unknown')}
                          tone={statusTone(document.index_status ?? 'unknown')}
                        />
                      </TableCell>
                      <TableCell className="max-w-sm truncate text-xs text-muted-foreground">
                        {document.last_error ?? '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Dialog
                          onOpenChange={(open) => {
                            if (!open) {
                              setSelectedDocument(null)
                              return
                            }
                            setSelectedDocument(document)
                            if (onLoadDocumentDetail) {
                              void onLoadDocumentDetail(document.doc_id)
                            }
                          }}
                        >
                          <DialogTrigger asChild>
                            <Button type="button" variant="outline" className="rounded-xl">
                              查看详情
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="sm:max-w-3xl">
                            <DialogHeader>
                              <div className="flex items-center gap-2">
                                <DialogTitle>文档只读详情</DialogTitle>
                                <Badge
                                  variant="outline"
                                  className="rounded-full border-border/70 bg-background/60"
                                >
                                  只读
                                </Badge>
                              </div>
                              <DialogDescription>
                                这里展示 SQLite 中的只读元数据，用于核对索引结果。
                              </DialogDescription>
                            </DialogHeader>
                            {selectedDetail ? (
                              <ReadOnlyDocumentDetail
                                document={selectedDetail}
                                loading={documentDetailLoading}
                              />
                            ) : (
                              <p className="text-sm text-muted-foreground">
                                请选择文档后查看详情。
                              </p>
                            )}
                          </DialogContent>
                        </Dialog>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                      当前过滤条件下暂无文档。
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
}) {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{displayLabel(label)}</p>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="rounded-2xl">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {displayLabel(option)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

function QuickLinkCard({
  title,
  description,
  to,
}: {
  title: string
  description: string
  to: string
}) {
  return (
    <Link
      to={to}
      className="rounded-2xl border border-border/70 bg-background/55 p-4 transition hover:border-primary/40 hover:bg-background/75"
    >
      <p className="font-medium">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
    </Link>
  )
}

function ActionButton({
  label,
  testId,
  onClick,
  disabled,
}: {
  label: string
  testId?: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <Button
      type="button"
      variant="outline"
      className="w-full rounded-2xl"
      data-testid={testId}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </Button>
  )
}

/**
 * Render a compact label/value pair for status and detail summaries.
 */
function InfoRow({
  label,
  value,
  testId,
}: {
  label: string
  value: string
  testId?: string
}) {
  return (
    <div
      className="flex items-start justify-between gap-4 rounded-2xl border border-border/70 bg-background/45 px-4 py-3"
      data-testid={testId}
    >
      <span className="text-muted-foreground">{label}</span>
      <span className="max-w-[60%] text-right text-sm font-medium">{value}</span>
    </div>
  )
}

/**
 * Present document metadata in a read-only layout so operators can verify indexed records safely.
 */
function ReadOnlyDocumentDetail({
  document,
  loading,
}: {
  document: DocumentRecord | DocumentDetail
  loading: boolean
}) {
  return (
    <div className="grid gap-3">
      {loading ? (
        <p className="text-sm text-muted-foreground">正在读取最新详情...</p>
      ) : null}
      <InfoRow label="标题" value={document.title ?? '—'} />
      <InfoRow label="路径" value={document.path} />
      <InfoRow label="Kit" value={document.kit ?? '—'} />
      <InfoRow
        label="页面类型"
        value={document.page_kind ? displayLabel(document.page_kind) : '—'}
      />
      <InfoRow
        label="索引状态"
        value={displayLabel(document.index_status ?? 'unknown')}
      />
      <InfoRow
        label="Chunk 数"
        value={`${document.indexed_chunk_count ?? 0} / ${document.chunk_count ?? 0}`}
      />
      <InfoRow label="错误信息" value={document.last_error ?? '—'} />
      <InfoRow label="最近索引" value={formatDate(document.last_indexed_at)} />
      {'source_url' in document ? (
        <InfoRow label="源地址" value={document.source_url ?? '—'} />
      ) : null}
      {'top_dir' in document ? (
        <InfoRow label="一级目录" value={document.top_dir ?? '—'} />
      ) : null}
      {'sub_dir' in document ? (
        <InfoRow label="子目录" value={document.sub_dir ?? '—'} />
      ) : null}
      {'subsystem' in document ? (
        <InfoRow label="子系统" value={document.subsystem ?? '—'} />
      ) : null}
      {'owner' in document ? (
        <InfoRow label="Owner" value={document.owner ?? '—'} />
      ) : null}
      {'created_at' in document ? (
        <InfoRow label="创建时间" value={formatDate(document.created_at)} />
      ) : null}
    </div>
  )
}
