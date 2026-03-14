# OpenHarmony Docs RAG - MCP Server

MCP Server for OpenHarmony Chinese documentation RAG system.

## Available Tools

### 1. oh_docs_rag_query

Ask a question about OpenHarmony documentation and get an answer with citations.

**Parameters:**
- `query` (required): The question to ask
- `top_k` (optional): Number of documents to retrieve (default: 6)
- `kit` (optional): Filter by Kit (e.g., ArkUI, ArkTS)
- `top_dir` (optional): Filter by top directory (e.g., application-dev, design)

**Example:**
```json
{
  "query": "如何创建 UIAbility 组件？",
  "top_k": 6
}
```

### 2. oh_docs_rag_retrieve

Search OpenHarmony documentation and retrieve relevant chunks without generating an answer.

**Parameters:**
- `query` (required): The search query
- `top_k` (optional): Number of results to return (default: 10)
- `kit` (optional): Filter by Kit
- `top_dir` (optional): Filter by top directory

**Example:**
```json
{
  "query": "ArkUI 组件",
  "top_k": 10,
  "kit": "ArkUI"
}
```

### 3. oh_docs_rag_sync_repo

Sync the OpenHarmony documentation repository to get the latest updates.

**Parameters:** None

### 4. oh_docs_rag_stats

Get statistics about the indexed OpenHarmony documentation.

**Parameters:** None

## Setup

### 1. Start the RAG API

```bash
cd openharmony-docs-rag
python app/main.py
```

### 2. Use the MCP Server

```python
from mcp.server import OpenHarmonyDocsRAGMCP

mcp = OpenHarmonyDocsRAGMCP(api_base_url="http://localhost:8000")

# List tools
tools = mcp.get_tools()

# Call a tool
result = await mcp.call_tool(
    "oh_docs_rag_query",
    {"query": "如何创建 UIAbility 组件？"}
)
```

## Configuration

The MCP server connects to the RAG API at `http://localhost:8000` by default.

To use a different URL:

```python
mcp = OpenHarmonyDocsRAGMCP(api_base_url="http://your-api-url:8000")
```

## Integration with Claude Code

To integrate with Claude Code, add the MCP server to your MCP configuration.

## Notes

- All requests include `X-Caller-Type: mcp` header for tracking
- Query tool has 60s timeout (for LLM generation)
- Retrieve tool has 30s timeout
- Sync repo tool has 300s timeout (5 minutes)
