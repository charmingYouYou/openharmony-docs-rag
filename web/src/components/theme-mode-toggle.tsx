import { LaptopMinimal, MoonStar, SunMedium } from 'lucide-react'
import { useTheme } from 'next-themes'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const modes = [
  { value: 'light', label: '浅色', icon: SunMedium },
  { value: 'dark', label: '深色', icon: MoonStar },
  { value: 'system', label: '跟随系统', icon: LaptopMinimal },
] as const

export function ThemeModeToggle() {
  const { setTheme, resolvedTheme, theme } = useTheme()
  const currentMode = theme ?? resolvedTheme ?? 'system'

  return (
    <div className="inline-flex rounded-2xl border border-border/70 bg-card/70 p-1 shadow-[0_16px_40px_rgba(1,8,20,0.18)]">
      {modes.map((mode) => {
        const Icon = mode.icon
        const active = currentMode === mode.value
        return (
          <Button
            key={mode.value}
            type="button"
            variant="ghost"
            size="sm"
            className={cn(
              'rounded-xl px-3 text-xs',
              active
                ? 'bg-primary text-primary-foreground shadow-[0_0_24px_rgba(32,197,255,0.3)]'
                : 'text-muted-foreground'
            )}
            onClick={() => setTheme(mode.value)}
          >
            <Icon className="mr-2 size-4" />
            {mode.label}
          </Button>
        )
      })}
    </div>
  )
}
