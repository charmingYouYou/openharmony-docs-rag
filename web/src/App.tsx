/**
 * Application shell for the deployed OpenHarmony Docs RAG console.
 */
import { ThemeProvider } from 'next-themes'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Toaster } from '@/components/ui/sonner'
import { AppSidebar } from '@/components/app-sidebar'
import { ThemeModeToggle } from '@/components/theme-mode-toggle'
import { StatusBadge } from '@/components/status-badge'
import { displayLabel } from '@/lib/display'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useConsoleData } from '@/hooks/use-console-data'
import {
  ApiLabPage,
  BuildCenterPage,
  ChatPage,
  IndexExplorerPage,
  IntegrationsPage,
  ServicesPage,
  WorkspacePage,
} from '@/pages/console-pages'

const pageCopy = {
  '/': {
    title: '工作台',
    description: '以任务流的方式完成构建、调试与集成配置。',
  },
  '/builds': {
    title: '构建中心',
    description: '关注阶段摘要、实时日志、安全暂停与增量恢复。',
  },
  '/lab': {
    title: '接口实验室',
    description: '带默认请求体的 API 调试台，适合验证原始 JSON 响应。',
  },
  '/chat': {
    title: '智能问答',
    description: '直接调用 /query，展示引用、追踪 ID、耗时和意图结果。',
  },
  '/services': {
    title: '服务状态',
    description: '查看端口、能力摘要和 deploy/app.env 原始配置。',
  },
  '/integrations': {
    title: '集成指南',
    description: '用中文说明 Skill 与 MCP 的本地接入步骤。',
  },
  '/explorer': {
    title: '索引浏览',
    description: '查看统计分布并按索引状态过滤已索引文档。',
  },
} as const

/**
 * Render the routed console experience around the shared deployment workspace chrome.
 */
function ConsoleShell() {
  const location = useLocation()
  const currentPage = pageCopy[location.pathname as keyof typeof pageCopy] ?? pageCopy['/']
  const consoleData = useConsoleData()

  return (
    <SidebarProvider>
      <AppSidebar latestRun={consoleData.latestRun} />
      <SidebarInset className="bg-transparent">
        <header className="sticky top-0 z-30 flex h-18 items-center gap-4 border-b border-border/70 bg-background/80 px-4 backdrop-blur-xl md:px-6">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="h-6" />
          <div className="min-w-0 flex-1">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
              OpenHarmony 文档控制台
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h1 className="truncate text-xl font-semibold tracking-tight">{currentPage.title}</h1>
              <StatusBadge
                label={displayLabel(consoleData.latestRun.status)}
                tone={
                  consoleData.latestRun.status === 'completed'
                    ? 'healthy'
                    : consoleData.latestRun.status === 'paused'
                      ? 'paused'
                      : consoleData.latestRun.status === 'failed'
                        ? 'danger'
                        : 'running'
                }
                pulse={consoleData.latestRun.status === 'running'}
              />
            </div>
            <p className="mt-1 truncate text-sm text-muted-foreground">
              {currentPage.description}
            </p>
          </div>
          <div className="hidden items-center gap-3 lg:flex">
            <Button
              variant="outline"
              className="rounded-2xl"
              onClick={() => void consoleData.beginBuild('sync_incremental')}
            >
              启动默认工作流
            </Button>
            <ThemeModeToggle />
          </div>
        </header>
        <main className="min-h-[calc(100vh-4.5rem)] px-4 py-6 md:px-6">
          <Routes>
            <Route
              path="/"
              element={
                <WorkspacePage
                  latestRun={consoleData.latestRun}
                  services={consoleData.services}
                  stats={consoleData.stats}
                  onStartBuild={consoleData.beginBuild}
                  onPause={consoleData.requestPause}
                  onResume={consoleData.requestResume}
                />
              }
            />
            <Route
              path="/builds"
              element={
                <BuildCenterPage
                  latestRun={consoleData.latestRun}
                  logs={consoleData.logs}
                  onStartBuild={consoleData.beginBuild}
                  onPause={consoleData.requestPause}
                  onResume={consoleData.requestResume}
                />
              }
            />
            <Route path="/lab" element={<ApiLabPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route
              path="/services"
              element={
                <ServicesPage
                  services={consoleData.services}
                  capabilities={consoleData.capabilities}
                  envPayload={consoleData.envPayload}
                  onRefreshServices={consoleData.refreshServices}
                  onSaveEnv={consoleData.persistEnv}
                />
              }
            />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route
              path="/explorer"
              element={
                <IndexExplorerPage
                  stats={consoleData.stats}
                  documents={consoleData.documents}
                  topDirOptions={consoleData.topDirOptions}
                  pageKindOptions={consoleData.pageKindOptions}
                  onRefreshDocuments={consoleData.refreshDocuments}
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

/**
 * Mount the routed console with theme, tooltip, and toaster providers.
 */
function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <TooltipProvider>
        <BrowserRouter>
          <ConsoleShell />
        </BrowserRouter>
        <Toaster richColors position="top-right" />
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
