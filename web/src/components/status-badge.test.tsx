import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusBadge } from './status-badge'

describe('StatusBadge', () => {
  it('在浅色模式下为暂停状态使用深色文本样式', () => {
    render(<StatusBadge label="已暂停" tone="paused" />)

    const badge = screen.getByText('已暂停').closest('[data-slot="badge"]')
    expect(badge?.className).toContain('text-amber-800')
    expect(badge?.className).toContain('dark:text-amber-200')
    expect(badge?.className).not.toContain('text-amber-100')
  })

  it('在浅色模式下为正常状态使用深色文本样式', () => {
    render(<StatusBadge label="正常" tone="healthy" />)

    const badge = screen.getByText('正常').closest('[data-slot="badge"]')
    expect(badge?.className).toContain('text-emerald-800')
    expect(badge?.className).toContain('dark:text-emerald-200')
    expect(badge?.className).not.toContain('text-emerald-100')
  })
})
