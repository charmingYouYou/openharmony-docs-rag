/**
 * Regression tests for light-theme readability and deploy-time env guidance.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { EnvPayload, ServiceStatus } from '@/lib/types'

import { ServicesPage } from './console-pages'

const services: ServiceStatus[] = [
  {
    name: 'API',
    status: 'healthy',
    host: '127.0.0.1',
    port: 8000,
    details: '运行正常',
  },
]

const envPayload: EnvPayload = {
  raw: 'OPENAI_API_KEY=test',
  warnings: [],
  last_modified: '2026-03-15T10:00:00.000Z',
}

describe('ServicesPage', () => {
  it('在浅色主题下为校验提示使用深色前景', () => {
    render(
      <ServicesPage
        services={services}
        capabilities={null}
        envPayload={envPayload}
        onRefreshServices={async () => undefined}
        onSaveEnv={async () => undefined}
      />,
    )

    const warningCard = screen.getByText('校验提示').closest('div')
    const warningList = screen.getByText(/当前未检测到核心字段缺失。/).closest('ul')
    const warningCardClasses = warningCard?.className.split(/\s+/) ?? []
    const warningListClasses = warningList?.className.split(/\s+/) ?? []

    expect(warningCardClasses).toContain('text-amber-900')
    expect(warningCardClasses).toContain('dark:text-amber-100')
    expect(warningCardClasses).not.toContain('text-amber-100')
    expect(warningListClasses).toContain('text-amber-800/90')
    expect(warningListClasses).toContain('dark:text-amber-50/85')
    expect(warningListClasses).not.toContain('text-amber-50/85')
  })

  it('展示 deploy/app.env 作为当前 Docker 部署配置文件', () => {
    render(
      <ServicesPage
        services={services}
        capabilities={null}
        envPayload={envPayload}
        onRefreshServices={async () => undefined}
        onSaveEnv={async () => undefined}
      />,
    )

    expect(screen.getAllByText('deploy/app.env 配置')).toHaveLength(2)
    expect(
      screen.getAllByText(/当前编辑的是 Docker 部署运行时配置文件 deploy\/app\.env/),
    ).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: '保存 deploy/app.env' })).toHaveLength(2)
  })
})
