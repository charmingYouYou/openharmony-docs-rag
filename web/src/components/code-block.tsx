import { Check, Copy } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'

export function CodeBlock({
  title,
  code,
}: {
  title: string
  code: string
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-border/70 bg-black/75 shadow-[0_24px_60px_rgba(1,8,20,0.35)]">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <p className="text-sm font-medium text-white/80">{title}</p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-white/80 hover:bg-white/10 hover:text-white"
          onClick={() => void handleCopy()}
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
          {copied ? '已复制' : '复制'}
        </Button>
      </div>
      <ScrollArea className="max-h-96">
        <pre className="overflow-x-auto px-4 py-4 font-mono text-xs leading-6 text-cyan-50">
          <code>{code}</code>
        </pre>
      </ScrollArea>
    </div>
  )
}
