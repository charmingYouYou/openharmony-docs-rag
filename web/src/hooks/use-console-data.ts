import { useEffect, useMemo, useRef, useState } from 'react'

import {
  getApiBaseUrl,
  getBuildRun,
  getCapabilities,
  getStats,
  listBuildRuns,
  listDocuments,
  listServices,
  pauseBuild,
  readEnvFile,
  resumeBuild,
  saveEnvFile,
  startBuild,
} from '@/lib/api'
import {
  fallbackRun,
  fallbackServices,
  fallbackStats,
} from '@/lib/console-data'
import type {
  BuildMode,
  BuildRunSummary,
  CapabilitiesResponse,
  ConsoleLogEntry,
  DocumentsResponse,
  EnvPayload,
  ServiceStatus,
  StatsResponse,
} from '@/lib/types'

const TERMINAL_STATUSES = new Set(['paused', 'completed', 'failed'])

export function useConsoleData() {
  const [runs, setRuns] = useState<BuildRunSummary[]>([])
  const [activeRun, setActiveRun] = useState<BuildRunSummary | null>(null)
  const [logs, setLogs] = useState<ConsoleLogEntry[]>([])
  const [services, setServices] = useState<ServiceStatus[]>(fallbackServices)
  const [stats, setStats] = useState<StatsResponse>(fallbackStats)
  const [capabilities, setCapabilities] = useState<CapabilitiesResponse | null>(
    null
  )
  const [envPayload, setEnvPayload] = useState<EnvPayload>({
    raw: '',
    warnings: [],
    last_modified: null,
  })
  const [documents, setDocuments] = useState<DocumentsResponse>({
    documents: [],
    total: 0,
    limit: 50,
    offset: 0,
  })
  const [loading, setLoading] = useState({
    build: false,
    services: false,
    env: false,
    documents: false,
  })
  const [errors, setErrors] = useState<Record<string, string | null>>({})
  const lastSeqRef = useRef(0)

  const liveRun = activeRun ?? runs[0] ?? null
  const latestRun = activeRun ?? runs[0] ?? fallbackRun

  const mergeRun = (nextRun: BuildRunSummary) => {
    setActiveRun(nextRun)
    setRuns((currentRuns) => {
      const withoutCurrent = currentRuns.filter((run) => run.id !== nextRun.id)
      return [nextRun, ...withoutCurrent]
    })
  }

  const addLog = (entry: ConsoleLogEntry) => {
    setLogs((currentLogs) => {
      if (currentLogs.some((log) => log.seq === entry.seq)) {
        return currentLogs
      }
      return [...currentLogs, entry].slice(-200)
    })
  }

  const refreshRuns = async () => {
    try {
      const nextRuns = await listBuildRuns()
      setRuns(nextRuns)
      if (!activeRun && nextRuns[0]) {
        setActiveRun(nextRuns[0])
      }
    } catch (error) {
      setErrors((current) => ({
        ...current,
        runs: error instanceof Error ? error.message : '获取构建任务失败',
      }))
    }
  }

  const refreshServices = async () => {
    setLoading((current) => ({ ...current, services: true }))
    try {
      setServices(await listServices())
      setErrors((current) => ({ ...current, services: null }))
    } catch (error) {
      setErrors((current) => ({
        ...current,
        services: error instanceof Error ? error.message : '获取服务状态失败',
      }))
    } finally {
      setLoading((current) => ({ ...current, services: false }))
    }
  }

  const refreshStats = async () => {
    try {
      setStats(await getStats())
      setErrors((current) => ({ ...current, stats: null }))
    } catch (error) {
      setErrors((current) => ({
        ...current,
        stats: error instanceof Error ? error.message : '获取索引统计失败',
      }))
    }
  }

  const refreshCapabilities = async () => {
    try {
      setCapabilities(await getCapabilities())
    } catch {
      setCapabilities(null)
    }
  }

  const refreshEnv = async () => {
    setLoading((current) => ({ ...current, env: true }))
    try {
      setEnvPayload(await readEnvFile())
      setErrors((current) => ({ ...current, env: null }))
    } catch (error) {
      setErrors((current) => ({
        ...current,
        env: error instanceof Error ? error.message : '读取 .env 失败',
      }))
    } finally {
      setLoading((current) => ({ ...current, env: false }))
    }
  }

  const refreshDocuments = async (params?: {
    indexStatus?: string
    topDir?: string
    pageKind?: string
  }) => {
    setLoading((current) => ({ ...current, documents: true }))
    try {
      setDocuments(await listDocuments(params ?? {}))
      setErrors((current) => ({ ...current, documents: null }))
    } catch (error) {
      setErrors((current) => ({
        ...current,
        documents:
          error instanceof Error ? error.message : '获取索引文档列表失败',
      }))
    } finally {
      setLoading((current) => ({ ...current, documents: false }))
    }
  }

  const beginBuild = async (mode: BuildMode) => {
    setLoading((current) => ({ ...current, build: true }))
    try {
      const run = await startBuild(mode)
      lastSeqRef.current = 0
      setLogs([])
      mergeRun(run)
      setErrors((current) => ({ ...current, build: null }))
      return run
    } catch (error) {
      setErrors((current) => ({
        ...current,
        build: error instanceof Error ? error.message : '启动构建失败',
      }))
      throw error
    } finally {
      setLoading((current) => ({ ...current, build: false }))
    }
  }

  const requestPause = async (runId: string) => {
    const run = await pauseBuild(runId)
    mergeRun(run)
    return run
  }

  const requestResume = async (runId: string) => {
    lastSeqRef.current = 0
    setLogs([])
    const run = await resumeBuild(runId)
    mergeRun(run)
    return run
  }

  const persistEnv = async (raw: string) => {
    setLoading((current) => ({ ...current, env: true }))
    try {
      const payload = await saveEnvFile(raw)
      setEnvPayload(payload)
      setErrors((current) => ({ ...current, env: null }))
      return payload
    } catch (error) {
      setErrors((current) => ({
        ...current,
        env: error instanceof Error ? error.message : '保存 .env 失败',
      }))
      throw error
    } finally {
      setLoading((current) => ({ ...current, env: false }))
    }
  }

  useEffect(() => {
    void refreshRuns()
    void refreshServices()
    void refreshStats()
    void refreshCapabilities()
    void refreshEnv()
    void refreshDocuments()
  }, [])

  useEffect(() => {
    if (!liveRun?.id || typeof EventSource === 'undefined') {
      return
    }

    const eventSource = new EventSource(
      `${getApiBaseUrl()}/web/builds/${liveRun.id}/events`
    )

    const handleEvent = (type: string, rawEvent: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(rawEvent.data) as {
          seq?: number
          message: string
          stage?: string
          status?: string
        }
        const seq = payload.seq ?? lastSeqRef.current + 1
        if (seq <= lastSeqRef.current) {
          return
        }
        lastSeqRef.current = seq
        addLog({
          seq,
          type,
          message: payload.message,
          timestamp: new Date().toISOString(),
        })
      } catch {
        addLog({
          seq: lastSeqRef.current + 1,
          type,
          message: rawEvent.data,
          timestamp: new Date().toISOString(),
        })
      }
    }

    const progressHandler = (event: MessageEvent<string>) =>
      handleEvent('progress', event)
    const statusHandler = (event: MessageEvent<string>) => handleEvent('status', event)
    const errorHandler = (event: MessageEvent<string>) => handleEvent('error', event)
    const completedHandler = (event: MessageEvent<string>) =>
      handleEvent('completed', event)

    eventSource.addEventListener('progress', progressHandler)
    eventSource.addEventListener('status', statusHandler)
    eventSource.addEventListener('error', errorHandler)
    eventSource.addEventListener('completed', completedHandler)

    return () => {
      eventSource.close()
    }
  }, [liveRun?.id])

  useEffect(() => {
    if (!liveRun?.id || TERMINAL_STATUSES.has(liveRun.status)) {
      return
    }

    const interval = window.setInterval(async () => {
      try {
        mergeRun(await getBuildRun(liveRun.id))
        void refreshStats()
        void refreshServices()
      } catch {
        window.clearInterval(interval)
      }
    }, 2000)

    return () => window.clearInterval(interval)
  }, [liveRun?.id, liveRun?.status])

  const topDirOptions = useMemo(
    () => ['all', ...Object.keys(stats.by_top_dir)],
    [stats.by_top_dir]
  )
  const pageKindOptions = useMemo(
    () => ['all', ...Object.keys(stats.by_page_kind)],
    [stats.by_page_kind]
  )

  return {
    runs,
    latestRun,
    logs,
    services,
    stats,
    capabilities,
    envPayload,
    documents,
    loading,
    errors,
    topDirOptions,
    pageKindOptions,
    beginBuild,
    requestPause,
    requestResume,
    refreshServices,
    refreshStats,
    refreshEnv,
    persistEnv,
    refreshDocuments,
  }
}
