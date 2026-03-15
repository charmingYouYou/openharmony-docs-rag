import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import App from './App'

describe('OpenHarmony Docs RAG 控制台', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/')
  })

  it('显示中文一级导航', () => {
    render(<App />)

    expect(screen.getAllByText('工作台')[0]).toBeInTheDocument()
    expect(screen.getAllByText('构建中心')[0]).toBeInTheDocument()
    expect(screen.getAllByText('接口实验室')[0]).toBeInTheDocument()
    expect(screen.getAllByText('智能问答')[0]).toBeInTheDocument()
  })

  it('将运行状态显示为中文', () => {
    render(<App />)

    expect(screen.getAllByText('已暂停')[0]).toBeInTheDocument()
    expect(screen.queryByText('paused')).not.toBeInTheDocument()
  })

  it('首页不显示英文回答文案', () => {
    render(<App />)

    expect(screen.getAllByText('一条工作流，从文档同步到带引用回答验证。')[0]).toBeInTheDocument()
    expect(screen.queryByText(/grounded answer/i)).not.toBeInTheDocument()
  })

  it('在接口实验室中展示默认示例请求', () => {
    window.history.pushState({}, '', '/lab')
    render(<App />)

    expect(screen.getAllByText(/适合调试原始请求与响应/)[0]).toBeInTheDocument()
    expect(screen.getByDisplayValue(/如何创建 UIAbility 组件/)).toBeInTheDocument()
    expect(screen.getByDisplayValue(/"top_dir": "application-dev"/)).toBeInTheDocument()
  })

  it('进入索引浏览页时不会陷入重复刷新', () => {
    window.history.pushState({}, '', '/explorer')
    render(<App />)

    expect(screen.getByText('索引文档列表')).toBeInTheDocument()
    expect(screen.getByText('目录分布')).toBeInTheDocument()
  })
})
