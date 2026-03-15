---
name: openharmony-docs-rag
description: Use this skill when the user asks questions about OpenHarmony development documentation, APIs, design specs, or best practices and you need grounded answers from the local RAG service.
allowed-tools: Bash(curl)
---

# OpenHarmony Docs RAG Skill

Use the local OpenHarmony documentation RAG API instead of answering from memory when the task is about OpenHarmony docs, APIs, design rules, or official usage guidance.

## Configuration

- Recommended deployment API base URL: `http://<部署地址>:8000`
- Override with environment variable: `OPENHARMONY_RAG_API_BASE_URL`

## Primary Actions

### Ask a grounded question

Use `/query` when the user wants an answer with citations.

```bash
curl -s "$OPENHARMONY_RAG_API_BASE_URL/query" \
  -H "Content-Type: application/json" \
  -H "X-Caller-Type: skill" \
  -d '{
    "query": "如何创建 UIAbility 组件？",
    "top_k": 6
  }'
```

### Retrieve relevant chunks only

Use `/retrieve` when the user wants evidence or relevant passages without answer generation.

```bash
curl -s "$OPENHARMONY_RAG_API_BASE_URL/retrieve" \
  -H "Content-Type: application/json" \
  -H "X-Caller-Type: skill" \
  -d '{
    "query": "router.pushUrl 方法如何使用？",
    "top_k": 5
  }'
```

### Inspect index status

Use `/health` or `/stats` before relying on the service.

```bash
curl -s "$OPENHARMONY_RAG_API_BASE_URL/health"
curl -s "$OPENHARMONY_RAG_API_BASE_URL/stats"
```

## Operating Rules

- Prefer `/query` for user-facing answers and `/retrieve` for investigation.
- Surface citations when they exist.
- If the API reports low relevance or returns no citations, tell the user the docs do not support a confident answer.
- Do not invent OpenHarmony API details that are not present in the retrieved result.
