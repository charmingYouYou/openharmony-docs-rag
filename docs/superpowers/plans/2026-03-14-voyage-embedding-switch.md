# Voyage Embedding Switch Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace async-v2 embeddings with Voyage-compatible synchronous embeddings and move all model configuration into environment variables.

**Architecture:** Keep the existing RAG structure, but swap the embedding client from DashScope async batch tasks to a synchronous embeddings endpoint. Split chat and embedding configuration into env-backed settings so the runtime no longer contains provider/model defaults.

**Tech Stack:** FastAPI, Pydantic Settings, requests, pytest, Qdrant, SQLite

---

## Chunk 1: Define Env-Driven Embedding Contract

### Task 1: Add failing tests for Voyage settings and request shape

**Files:**
- Modify: `tests/test_async_v2_embedding.py`
- Test: `tests/test_async_v2_embedding.py`

- [ ] **Step 1: Rewrite the regression tests around Voyage behavior**
- [ ] **Step 2: Run `pytest tests/test_async_v2_embedding.py -q` and confirm failure against the current async-v2 implementation**
- [ ] **Step 3: Cover document embeddings, query embeddings, base URL normalization, and response parsing**

## Chunk 2: Replace Async-v2 Runtime Path

### Task 2: Refactor settings and embedder to env-only Voyage config

**Files:**
- Modify: `app/settings.py`
- Modify: `app/core/embedder.py`
- Modify: `app/services/answer_service.py`
- Modify: `app/api/health.py`

- [ ] **Step 1: Remove provider/model defaults from settings**
- [ ] **Step 2: Replace async task logic with synchronous embeddings calls**
- [ ] **Step 3: Update chat client settings to use env-backed generic LLM settings**
- [ ] **Step 4: Run the rewritten embedder tests until they pass**

### Task 3: Remove async-v2-only plumbing from runtime

**Files:**
- Modify: `app/main.py`
- Modify: `scripts/build_index.py`
- Delete: `app/utils/public_file_store.py`
- Delete: `scripts/prepare_batch_input.py`
- Delete: `scripts/submit_batch_task.py`

- [ ] **Step 1: Remove `/public` static hosting and async-v2 comments**
- [ ] **Step 2: Simplify indexing to direct batch embedding**
- [ ] **Step 3: Remove dead async helper files**
- [ ] **Step 4: Run targeted tests/import checks**

## Chunk 3: Update Docs and Verify Locally

### Task 4: Update env examples, README, and smoke verification

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Replace async-v2 setup and examples with env-only Voyage configuration**
- [ ] **Step 2: Configure local `.env` for the provided Voyage base URL and key**
- [ ] **Step 3: Run `pytest tests/test_async_v2_embedding.py tests/test_basic.py -q`**
- [ ] **Step 4: Probe the configured embeddings endpoint with a real request and report the actual result**
