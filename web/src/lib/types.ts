export type BuildMode = 'sync_incremental' | 'incremental' | 'full_rebuild'
export type BuildStatus =
  | 'queued'
  | 'running'
  | 'pausing'
  | 'paused'
  | 'completed'
  | 'failed'
export type BuildStage =
  | 'idle'
  | 'syncing_repo'
  | 'collecting_docs'
  | 'indexing'
  | 'paused'
  | 'completed'
  | 'failed'

export interface BuildRunSummary {
  id: string
  mode: BuildMode
  status: BuildStatus
  stage: BuildStage
  started_at: string
  updated_at: string
  processed_docs: number
  total_docs: number
  indexed_docs: number
  reindexed_docs: number
  skipped_docs: number
  failed_docs: number
  current_path: string
  can_pause: boolean
  can_resume: boolean
}

export interface ServiceStatus {
  name: string
  status: string
  host: string
  port: number
  details: string
}

export interface EnvPayload {
  raw: string
  warnings: string[]
  last_modified?: string | null
}

export interface CapabilitiesResponse {
  supported_intents: string[]
  supported_filters: string[]
  max_top_k: number
  embedding_model: string
  chat_model: string
}

export interface StatsResponse {
  total_documents: number
  by_top_dir: Record<string, number>
  by_kit: Record<string, number>
  by_page_kind: Record<string, number>
  document_types: {
    api_reference: number
    guide: number
    design_spec: number
  }
}

export interface DocumentRecord {
  doc_id: string
  path: string
  title?: string | null
  top_dir?: string | null
  page_kind?: string | null
  kit?: string | null
  index_status?: string | null
  last_error?: string | null
  indexed_chunk_count?: number
  chunk_count?: number
  last_indexed_at?: string | null
}

export interface DocumentsResponse {
  documents: DocumentRecord[]
  total: number
  limit: number
  offset: number
}

export interface Citation {
  path: string
  title?: string | null
  heading_path: string
  snippet: string
  source_url: string
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  trace_id: string
  latency_ms: number
  used_chunks: number
  intent: {
    type: string
    confidence: number
  }
}

export interface RetrievedChunk {
  chunk_id: string
  text: string
  heading_path: string
  score: number
  metadata: Record<string, unknown>
}

export interface RetrieveResponse {
  chunks: RetrievedChunk[]
  trace_id: string
  latency_ms: number
}

export interface BuildEventData {
  seq?: number
  message: string
  stage?: string
  status?: string
  total_docs?: number
  processed_docs?: number
  current_path?: string
}

export interface ConsoleLogEntry {
  seq: number
  type: string
  message: string
  timestamp: string
}
