/**
 * Tests for deployment-oriented API base URL resolution.
 */
import { describe, expect, it } from 'vitest'

import { resolveApiBaseUrl } from './api'

describe('resolveApiBaseUrl', () => {
  it('默认使用同源地址', () => {
    expect(resolveApiBaseUrl(undefined, 'http://demo.example.com')).toBe('http://demo.example.com')
    expect(resolveApiBaseUrl('', 'http://demo.example.com')).toBe('http://demo.example.com')
  })

  it('在显式配置时使用自定义 API 地址', () => {
    expect(resolveApiBaseUrl('https://rag-api.example.com', 'http://demo.example.com')).toBe(
      'https://rag-api.example.com',
    )
  })

  it('在没有浏览器 origin 时回退到本地默认地址', () => {
    expect(resolveApiBaseUrl(undefined, undefined)).toBe('http://127.0.0.1:8000')
  })
})
