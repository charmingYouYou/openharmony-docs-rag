/**
 * Regression tests for read-only document detail browsing in the explorer page.
 */
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DocumentsResponse, StatsResponse } from '@/lib/types'

import { IndexExplorerPage } from './console-pages'

const stats: StatsResponse = {
  total_documents: 1,
  by_top_dir: { 'application-dev': 1 },
  by_kit: { ArkUI: 1 },
  by_page_kind: { guide: 1 },
  document_types: {
    api_reference: 0,
    guide: 1,
    design_spec: 0,
  },
}

const documents: DocumentsResponse = {
  documents: [
    {
      doc_id: 'doc-1',
      path: 'zh-cn/application-dev/doc-1.md',
      title: 'Doc 1',
      top_dir: 'application-dev',
      page_kind: 'guide',
      kit: 'ArkUI',
      index_status: 'ready',
      last_error: null,
      indexed_chunk_count: 3,
      chunk_count: 3,
      last_indexed_at: '2026-03-15T10:00:00.000Z',
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
}

describe('IndexExplorerPage', () => {
  it('展示文档只读详情且不提供保存入口', () => {
    render(
      <IndexExplorerPage
        stats={stats}
        documents={documents}
        topDirOptions={['all', 'application-dev']}
        pageKindOptions={['all', 'guide']}
        onRefreshDocuments={async () => undefined}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '查看详情' }))

    expect(screen.getByText('文档只读详情')).toBeInTheDocument()
    expect(screen.getByText('Doc 1')).toBeInTheDocument()
    expect(screen.getAllByText('zh-cn/application-dev/doc-1.md')).toHaveLength(2)
    expect(screen.getByText('只读')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /保存/i })).not.toBeInTheDocument()
  })
})
