# Incremental Indexing Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add document-level incremental indexing and resume support so unchanged documents are skipped and interrupted runs do not require a destructive full rebuild.

**Architecture:** Persist indexing state in SQLite, compare source content and indexing signature on each run, and reindex only dirty documents. Process documents independently so a failed document cannot poison later batches and partial vectors are cleaned up before retry.

**Tech Stack:** Python, SQLite, Qdrant, FastAPI project utilities, pytest

---

## Chunk 1: Persist Indexing State

### Task 1: Extend SQLite metadata for incremental indexing

**Files:**
- Modify: `app/storage/models.py`
- Modify: `app/storage/sqlite_client.py`
- Test: `tests/test_incremental_indexing.py`

- [ ] **Step 1: Write failing tests for new metadata fields and migrations**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Add indexing-state fields to `DocumentModel` and SQLite schema migration logic**
- [ ] **Step 4: Run the targeted tests and confirm they pass**

## Chunk 2: Incremental Build Decisions

### Task 2: Teach the index builder to skip unchanged documents

**Files:**
- Modify: `scripts/build_index.py`
- Modify: `app/core/chunker.py` or related helpers only if a stable version constant is needed
- Test: `tests/test_incremental_indexing.py`

- [ ] **Step 1: Write failing tests for skip/reindex decisions based on content hash and index signature**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Add helpers to compute content hash and index signature, then implement incremental skip logic**
- [ ] **Step 4: Run the targeted tests and confirm they pass**

### Task 3: Isolate failures at document scope

**Files:**
- Modify: `scripts/build_index.py`
- Modify: `app/storage/qdrant_client.py` if safer delete helpers are needed
- Test: `tests/test_incremental_indexing.py`

- [ ] **Step 1: Write failing tests for interrupted/failed documents not poisoning later documents**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Refactor the builder to process one document at a time, clean partial vectors on failure, and mark rows `failed`**
- [ ] **Step 4: Run the targeted tests and confirm they pass**

## Chunk 3: CLI and Verification

### Task 4: Add explicit full rebuild mode and stale-document cleanup

**Files:**
- Modify: `scripts/build_index.py`
- Test: `tests/test_incremental_indexing.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for `--full-rebuild` and deleted-source cleanup**
- [ ] **Step 2: Run the targeted tests and confirm they fail**
- [ ] **Step 3: Implement CLI mode selection and stale-document cleanup**
- [ ] **Step 4: Run the targeted tests and confirm they pass**

### Task 5: Verify with real indexing behavior

**Files:**
- Modify: `README.md`
- Test: `tests/test_incremental_indexing.py`

- [ ] **Step 1: Document default incremental behavior and explicit full rebuild usage**
- [ ] **Step 2: Run `pytest tests/test_incremental_indexing.py tests/test_chunker.py tests/test_async_v2_embedding.py tests/test_qdrant_client.py tests/test_basic.py -q`**
- [ ] **Step 3: Run a real build twice and verify the second run skips unchanged docs**
