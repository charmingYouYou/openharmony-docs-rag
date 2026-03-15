import { AlertTriangle, CheckCircle2, LoaderCircle, PauseCircle } from 'lucide-react'

import { displayLabel } from '@/lib/display'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

type Tone = 'healthy' | 'running' | 'paused' | 'warning' | 'danger' | 'unknown'

const toneStyles: Record<Tone, string> = {
  healthy:
    'border border-emerald-500/25 bg-emerald-500/12 text-emerald-800 dark:text-emerald-200',
  running:
    'border border-cyan-500/25 bg-cyan-500/12 text-cyan-800 dark:text-cyan-200',
  paused:
    'border border-amber-500/25 bg-amber-500/12 text-amber-800 dark:text-amber-200',
  warning:
    'border border-orange-500/25 bg-orange-500/12 text-orange-800 dark:text-orange-200',
  danger:
    'border border-rose-500/25 bg-rose-500/12 text-rose-800 dark:text-rose-200',
  unknown:
    'border border-border/70 bg-muted/60 text-foreground/80 dark:text-muted-foreground',
}

const toneIcons = {
  healthy: CheckCircle2,
  running: LoaderCircle,
  paused: PauseCircle,
  warning: AlertTriangle,
  danger: AlertTriangle,
  unknown: AlertTriangle,
} as const

export function StatusBadge({
  label,
  tone,
  pulse = false,
}: {
  label: string
  tone: Tone
  pulse?: boolean
}) {
  const Icon = toneIcons[tone]
  return (
    <Badge className={cn('gap-1.5 rounded-full px-2.5 py-1 text-[11px]', toneStyles[tone])}>
      <Icon className={cn('size-3.5', pulse && 'animate-spin')} />
      {displayLabel(label)}
    </Badge>
  )
}
