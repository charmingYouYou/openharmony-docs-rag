/**
 * API client helpers for the deployed web console.
 */
import type {
  BuildMode,
  BuildRunSummary,
  CapabilitiesResponse,
  DocumentsResponse,
  EnvPayload,
  QueryResponse,
  RetrieveResponse,
  ServiceStatus,
  StatsResponse,
} from '@/lib/types'

/**
 * Resolve the backend base URL, preferring explicit configuration and otherwise using same-origin.
 */
export function resolveApiBaseUrl(explicitBaseUrl?: string, currentOrigin?: string) {
  if (explicitBaseUrl?.trim()) {
    return explicitBaseUrl
  }
  if (currentOrigin?.trim()) {
    return currentOrigin
  }
  return 'http://127.0.0.1:8000'
}

const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  typeof window !== 'undefined' ? window.location.origin : undefined,
)

/**
 * Execute a JSON request against the RAG API and surface server-side detail messages.
 */
async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response
      .json()
      .then((payload) => payload.detail as string | undefined)
      .catch(() => undefined)
    throw new Error(detail ?? `请求失败：${response.status}`)
  }

  return response.json() as Promise<T>
}

/**
 * Return the resolved API base URL currently used by the web console.
 */
export function getApiBaseUrl() {
  return API_BASE_URL
}

export function listBuildRuns() {
  return requestJson<BuildRunSummary[]>('/web/builds')
}

export function getBuildRun(runId: string) {
  return requestJson<BuildRunSummary>(`/web/builds/${runId}`)
}

export function startBuild(mode: BuildMode) {
  return requestJson<BuildRunSummary>('/web/builds', {
    method: 'POST',
    body: JSON.stringify({ mode }),
  })
}

export function pauseBuild(runId: string) {
  return requestJson<BuildRunSummary>(`/web/builds/${runId}/pause`, {
    method: 'POST',
  })
}

export function resumeBuild(runId: string) {
  return requestJson<BuildRunSummary>(`/web/builds/${runId}/resume`, {
    method: 'POST',
  })
}

export function listServices() {
  return requestJson<ServiceStatus[]>('/web/services')
}

export function readEnvFile() {
  return requestJson<EnvPayload>('/web/env')
}

export function saveEnvFile(raw: string) {
  return requestJson<EnvPayload>('/web/env', {
    method: 'PUT',
    body: JSON.stringify({ raw }),
  })
}

export function getStats() {
  return requestJson<StatsResponse>('/stats')
}

export function getCapabilities() {
  return requestJson<CapabilitiesResponse>('/capabilities')
}

export function listDocuments(params: {
  indexStatus?: string
  topDir?: string
  pageKind?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params.indexStatus && params.indexStatus !== 'all') {
    search.set('index_status', params.indexStatus)
  }
  if (params.topDir && params.topDir !== 'all') {
    search.set('top_dir', params.topDir)
  }
  if (params.pageKind && params.pageKind !== 'all') {
    search.set('page_kind', params.pageKind)
  }
  search.set('limit', String(params.limit ?? 50))
  search.set('offset', String(params.offset ?? 0))
  return requestJson<DocumentsResponse>(`/documents?${search.toString()}`)
}

export function runRetrieve(payload: unknown) {
  return requestJson<RetrieveResponse>('/retrieve', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function runQuery(payload: unknown) {
  return requestJson<QueryResponse>('/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
