/**
 * Regression tests for stable build-center selectors used by Playwright E2E.
 */
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { BuildRunSummary, ConsoleLogEntry } from '@/lib/types'

import { BuildCenterPage } from './console-pages'

const latestRun: BuildRunSummary = {
  id: 'run-1',
  mode: 'incremental',
  status: 'paused',
  stage: 'paused',
  started_at: '2026-03-15T10:00:00.000Z',
  updated_at: '2026-03-15T10:05:00.000Z',
  processed_docs: 12,
  total_docs: 20,
  indexed_docs: 10,
  reindexed_docs: 2,
  skipped_docs: 3,
  failed_docs: 0,
  current_path: 'zh-cn/application-dev/doc.md',
  can_pause: false,
  can_resume: true,
}

const logs: ConsoleLogEntry[] = [
  {
    seq: 1,
    type: 'progress',
    message: '进入增量构建，跳过仓库同步',
    timestamp: '2026-03-15T10:00:00.000Z',
  },
]

describe('BuildCenterPage', () => {
  it('为构建控制按钮、状态和日志面板提供稳定的测试选择器', () => {
    render(
      <BuildCenterPage
        latestRun={latestRun}
        logs={logs}
        onStartBuild={async () => undefined}
        onPause={async () => undefined}
        onResume={async () => undefined}
      />,
    )

    expect(screen.getByTestId('build-start-sync')).toHaveTextContent('同步并增量构建')
    expect(screen.getByTestId('build-start-incremental')).toHaveTextContent('仅增量构建')
    expect(screen.getByTestId('build-pause-resume')).toHaveTextContent('继续增量恢复')
    expect(screen.getByTestId('build-full-rebuild')).toHaveTextContent('全量重建')
    expect(screen.getByTestId('build-status')).toHaveTextContent('已暂停')
    expect(screen.getByTestId('build-log-panel')).toHaveTextContent('进入增量构建，跳过仓库同步')
    expect(screen.getByTestId('build-stat-skipped')).toHaveTextContent('3')
  })
})
