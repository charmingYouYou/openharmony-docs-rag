# Incremental Indexing Design

## Goal

Replace the current always-clear rebuild flow with a document-level incremental indexer that can resume after interruption and skip unchanged documents, so repeated runs do not repay the embedding cost for already indexed content.

## Current Problem

The current build script clears SQLite and Qdrant at startup, then streams embeddings into Qdrant. If the run fails halfway, successful work is discarded on the next retry. SQLite only stores document metadata, so it cannot tell whether a document is already indexed for the current embedding model and chunking logic.

## Chosen Approach

Use document-level indexing state in SQLite and make incremental mode the default:

- keep existing vectors and metadata by default
- compare each source document against stored indexing metadata
- skip documents whose content and indexing signature are unchanged and already marked ready
- reindex only documents that are changed, failed previously, or were interrupted mid-run
- delete vectors and metadata for source files that no longer exist
- keep an explicit full-rebuild mode for destructive rebuilds

## Indexing Metadata

Each SQLite document row will additionally store:

- `content_hash`: hash of the raw Markdown content
- `index_signature`: hash of indexing-relevant configuration
- `index_status`: `ready`, `indexing`, or `failed`
- `indexed_chunk_count`: persisted progress for observability
- `last_error`: most recent indexing error

The `index_signature` will cover the document embedding configuration and chunking behavior, so changing model/base URL/document prefix/chunk settings automatically invalidates stale rows.

## Runtime Flow

1. Initialize SQLite schema and migrate missing columns.
2. If `--full-rebuild` is requested, clear SQLite and Qdrant and run a full rebuild.
3. Otherwise, load existing SQLite rows by path and remove stale rows/vectors for deleted source files.
4. For each source document:
   - parse and chunk it
   - compute `content_hash` and current `index_signature`
   - if existing row is `ready` and both hashes match, skip
   - otherwise delete prior vectors for that doc, mark row as `indexing`, and rebuild only that document
5. On successful document completion, mark the row `ready`.
6. On failure, delete any partial vectors for that document, mark the row `failed`, store the error, and continue with the next document.

## Why Document-Level

Document-level reindexing is the best fit for the current codebase:

- it avoids full rebuilds and repeated token spend
- it gives reliable resume semantics after interruption
- it keeps the implementation smaller than chunk-level embedding caches
- it prevents partial documents from remaining in Qdrant

This is intentionally smaller than chunk-level embedding deduplication. If token spend remains a problem after this change, chunk-level caching can be added later on top of the document-level state.
