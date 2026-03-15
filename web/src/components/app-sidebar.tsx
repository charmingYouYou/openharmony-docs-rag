import {
  Activity,
  Files,
  FlaskConical,
  LayoutDashboard,
  MessagesSquare,
  PlugZap,
  Workflow,
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'

import { navigationItems } from '@/lib/console-data'
import { displayLabel } from '@/lib/display'
import type { BuildRunSummary } from '@/lib/types'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import { Badge } from '@/components/ui/badge'

const iconMap = {
  'layout-dashboard': LayoutDashboard,
  workflow: Workflow,
  'flask-conical': FlaskConical,
  'messages-square': MessagesSquare,
  activity: Activity,
  'plug-zap': PlugZap,
  files: Files,
} as const

export function AppSidebar({
  latestRun,
}: {
  latestRun: BuildRunSummary
}) {
  const location = useLocation()

  return (
    <Sidebar className="border-r border-sidebar-border/70 bg-sidebar/90 backdrop-blur-xl">
      <SidebarHeader className="border-b border-sidebar-border/70">
        <div className="space-y-3 px-2 py-2">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-2xl bg-sidebar-primary text-sidebar-primary-foreground shadow-[0_0_30px_rgba(32,197,255,0.25)]">
              <Workflow className="size-5" />
            </div>
            <div className="space-y-1">
              <p className="text-xs uppercase tracking-[0.3em] text-sidebar-foreground/60">
                OpenHarmony
              </p>
              <h1 className="text-sm font-semibold tracking-wide text-sidebar-foreground">
                文档检索增强控制台
              </h1>
            </div>
          </div>
          <div className="rounded-2xl border border-sidebar-border/60 bg-black/15 p-3 text-xs text-sidebar-foreground/70">
            <div className="flex items-center justify-between">
              <span>当前任务</span>
              <Badge className="rounded-full border border-cyan-400/20 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/10">
                {displayLabel(latestRun.status)}
              </Badge>
            </div>
            <p className="mt-2 font-mono text-[11px] text-sidebar-foreground/55">
              {latestRun.id}
            </p>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-2 py-4">
        <SidebarGroup>
          <SidebarGroupLabel className="text-[11px] uppercase tracking-[0.24em] text-sidebar-foreground/45">
            导航
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navigationItems.map((item) => {
                const Icon = iconMap[item.icon]
                return (
                  <SidebarMenuItem key={item.to}>
                    <SidebarMenuButton
                      asChild
                      size="lg"
                      tooltip={item.label}
                      isActive={location.pathname === item.to}
                    >
                      <NavLink
                        to={item.to}
                        className="group flex items-center gap-3"
                      >
                        <Icon className="size-4" />
                        <span>{item.label}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border/70 p-3">
        <div className="rounded-2xl border border-sidebar-border/60 bg-black/10 p-3 text-xs leading-5 text-sidebar-foreground/70">
          <p className="font-semibold text-sidebar-foreground">本地运维台</p>
          <p className="mt-1">支持建库、调试、问答、集成引导与服务观察。</p>
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
