# OpenHarmony Docs RAG - MCP Server

真正可运行的 MCP server 入口是 `rag_mcp.stdio_server`，它通过 stdio 暴露工具，并转发到本地 RAG API。

## Available Tools

- `oh_docs_rag_query`
- `oh_docs_rag_retrieve`
- `oh_docs_rag_sync_repo`
- `oh_docs_rag_stats`

## Setup

### 1. Start the RAG API

```bash
cd openharmony-docs-rag
./venv/bin/python app/main.py
```

### 2. Run the MCP server

```bash
OPENHARMONY_RAG_API_BASE_URL=http://127.0.0.1:8000 \
./venv/bin/python -m rag_mcp.stdio_server
```

## Client Configuration Example

将下面的配置片段加入你的 MCP client 配置即可：

```json
{
  "mcpServers": {
    "openharmony-docs-rag": {
      "command": "/absolute/path/to/openharmony-docs-rag/venv/bin/python",
      "args": ["-m", "rag_mcp.stdio_server"],
      "cwd": "/absolute/path/to/openharmony-docs-rag",
      "env": {
        "OPENHARMONY_RAG_API_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

## Programmatic Adapter

如果你只是想在 Python 中直接调用 MCP 风格的工具定义，而不是跑 stdio server，可以使用兼容适配层：

```python
from rag_mcp.http_adapter import OpenHarmonyDocsRAGMCP

mcp = OpenHarmonyDocsRAGMCP(api_base_url="http://127.0.0.1:8000")
tools = mcp.get_tools()
result = await mcp.call_tool("oh_docs_rag_query", {"query": "如何创建 UIAbility 组件？"})
```

## Notes

- MCP server 默认通过 `OPENHARMONY_RAG_API_BASE_URL` 读取 API 地址
- 工具返回的是结构化 JSON payload，适合 MCP client 继续加工
- 不要在 stdio server 中向 `stdout` 打日志，否则会污染 MCP 协议流
