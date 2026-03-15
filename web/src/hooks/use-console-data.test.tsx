/**
 * Regression tests for console data refresh behavior after saving runtime env.
 */
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useConsoleData } from './use-console-data'

const mockApi = vi.hoisted(() => ({
  getApiBaseUrl: vi.fn(() => 'http://127.0.0.1:8000'),
  getBuildRun: vi.fn(),
  getCapabilities: vi.fn(),
  getDocumentDetail: vi.fn(),
  getStats: vi.fn(),
  listBuildRuns: vi.fn(),
  listDocuments: vi.fn(),
  listServices: vi.fn(),
  pauseBuild: vi.fn(),
  readEnvFile: vi.fn(),
  resumeBuild: vi.fn(),
  saveEnvFile: vi.fn(),
  startBuild: vi.fn(),
}))

vi.mock('@/lib/api', () => mockApi)

class EventSourceMock {
  static instances: EventSourceMock[] = []

  constructor() {
    EventSourceMock.instances.push(this)
  }

  addEventListener() {}
  close() {}
}

function HookHarness() {
  const data = useConsoleData()

  return (
    <div>
      <button type="button" onClick={() => void data.persistEnv('API_PORT=9000\n')}>
        保存
      </button>
      <button type="button" onClick={() => void data.requestResume('run-1')}>
        恢复
      </button>
    </div>
  )
}

describe('useConsoleData', () => {
  afterEach(() => {
    cleanup()
  })

  beforeEach(() => {
    vi.clearAllMocks()
    EventSourceMock.instances = []
    mockApi.listBuildRuns.mockResolvedValue([
      {
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
      },
    ])
    mockApi.listServices.mockResolvedValue([
      {
        name: 'API',
        status: 'healthy',
        host: '127.0.0.1',
        port: 8000,
        details: '运行正常',
      },
    ])
    mockApi.getStats.mockResolvedValue({
      total_documents: 1,
      by_top_dir: { 'application-dev': 1 },
      by_kit: { ArkUI: 1 },
      by_page_kind: { guide: 1 },
      document_types: {
        api_reference: 0,
        guide: 1,
        design_spec: 0,
      },
    })
    mockApi.getCapabilities.mockResolvedValue({
      supported_intents: ['guide'],
      supported_filters: ['top_dir'],
      max_top_k: 50,
      embedding_model: 'Qwen/Qwen3-Embedding-4B',
      chat_model: 'qwen-max',
    })
    mockApi.readEnvFile.mockResolvedValue({
      raw: 'API_PORT=8000\n',
      warnings: [],
      last_modified: '2026-03-15T10:00:00.000Z',
    })
    mockApi.listDocuments.mockResolvedValue({
      documents: [],
      total: 0,
      limit: 50,
      offset: 0,
    })
    mockApi.saveEnvFile.mockResolvedValue({
      raw: 'API_PORT=9000\n',
      warnings: [],
      last_modified: '2026-03-15T10:05:00.000Z',
    })
    mockApi.resumeBuild.mockResolvedValue({
      id: 'run-1',
      mode: 'incremental',
      status: 'running',
      stage: 'collecting_docs',
      started_at: '2026-03-15T10:00:00.000Z',
      updated_at: '2026-03-15T10:06:00.000Z',
      processed_docs: 12,
      total_docs: 20,
      indexed_docs: 10,
      reindexed_docs: 2,
      skipped_docs: 3,
      failed_docs: 0,
      current_path: 'zh-cn/application-dev/doc.md',
      can_pause: true,
      can_resume: false,
    })
    vi.stubGlobal('EventSource', EventSourceMock)
  })

  it('在保存 deploy/app.env 后联动刷新服务、能力、统计和文档列表', async () => {
    render(<HookHarness />)

    await waitFor(() => {
      expect(mockApi.listServices).toHaveBeenCalledTimes(1)
      expect(mockApi.getCapabilities).toHaveBeenCalledTimes(1)
      expect(mockApi.getStats).toHaveBeenCalledTimes(1)
      expect(mockApi.listDocuments).toHaveBeenCalledTimes(1)
    })

    await act(async () => {
      screen.getByRole('button', { name: '保存' }).click()
    })

    await waitFor(() => {
      expect(mockApi.saveEnvFile).toHaveBeenCalledWith('API_PORT=9000\n')
      expect(mockApi.listServices).toHaveBeenCalledTimes(2)
      expect(mockApi.getCapabilities).toHaveBeenCalledTimes(2)
      expect(mockApi.getStats).toHaveBeenCalledTimes(2)
      expect(mockApi.listDocuments).toHaveBeenCalledTimes(2)
    })
  })

  it('在恢复已暂停任务后重新建立事件流订阅', async () => {
    render(<HookHarness />)

    await waitFor(() => {
      expect(EventSourceMock.instances).toHaveLength(1)
    })

    await act(async () => {
      screen.getByRole('button', { name: '恢复' }).click()
    })

    await waitFor(() => {
      expect(mockApi.resumeBuild).toHaveBeenCalledWith('run-1')
      expect(EventSourceMock.instances).toHaveLength(2)
    })
  })
})
