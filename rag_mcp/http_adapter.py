"""Legacy HTTP adapter for MCP-like access to the RAG API."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from app.clients.rag_api_client import RAGAPIClient


class OpenHarmonyDocsRAGMCP:
    """Backward-compatible adapter that exposes API-backed MCP tool methods."""

    def __init__(self, api_base_url: str | None = None):
        base_url = api_base_url or os.getenv(
            "OPENHARMONY_RAG_API_BASE_URL",
            "http://localhost:8000",
        )
        self.client = RAGAPIClient(base_url, caller_type="mcp")

    def get_tools(self) -> List[Dict[str, Any]]:
        """Return MCP-style tool definitions."""
        return [
            {
                "name": "oh_docs_rag_query",
                "description": "Ask a question about OpenHarmony documentation and get an answer with citations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The question to ask"},
                        "top_k": {
                            "type": "integer",
                            "description": "Number of documents to retrieve (default: 6)",
                            "default": 6,
                        },
                        "kit": {
                            "type": "string",
                            "description": "Filter by Kit (e.g., ArkUI, ArkTS)",
                        },
                        "top_dir": {
                            "type": "string",
                            "description": "Filter by top directory (e.g., application-dev, design)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "oh_docs_rag_retrieve",
                "description": "Search OpenHarmony documentation and retrieve relevant chunks without generating an answer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"},
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 10)",
                            "default": 10,
                        },
                        "kit": {
                            "type": "string",
                            "description": "Filter by Kit (e.g., ArkUI, ArkTS)",
                        },
                        "top_dir": {
                            "type": "string",
                            "description": "Filter by top directory (e.g., application-dev, design)",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "oh_docs_rag_sync_repo",
                "description": "Sync the OpenHarmony documentation repository to get the latest updates",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "oh_docs_rag_stats",
                "description": "Get statistics about the indexed OpenHarmony documentation",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one adapter-backed tool call."""
        filters = {
            key: arguments[key]
            for key in ("kit", "top_dir")
            if arguments.get(key)
        } or None

        if tool_name == "oh_docs_rag_query":
            return await self.client.query(
                arguments["query"],
                top_k=arguments.get("top_k", 6),
                filters=filters,
            )
        if tool_name == "oh_docs_rag_retrieve":
            return await self.client.retrieve(
                arguments["query"],
                top_k=arguments.get("top_k", 10),
                filters=filters,
            )
        if tool_name == "oh_docs_rag_sync_repo":
            return await self.client.sync_repo()
        if tool_name == "oh_docs_rag_stats":
            return await self.client.stats()
        raise ValueError(f"Unknown tool: {tool_name}")
