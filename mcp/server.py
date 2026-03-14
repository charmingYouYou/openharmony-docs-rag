"""
MCP Server for OpenHarmony Docs RAG

This server exposes the RAG system as MCP tools.
"""

import httpx
import json
from typing import Optional, Dict, Any, List


class OpenHarmonyDocsRAGMCP:
    """MCP Server for OpenHarmony documentation RAG system."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the MCP server.

        Args:
            api_base_url: Base URL of the RAG API
        """
        self.api_base_url = api_base_url
        self.headers = {"X-Caller-Type": "mcp"}

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available MCP tools.

        Returns:
            List of tool definitions
        """
        return [
            {
                "name": "oh_docs_rag_query",
                "description": "Ask a question about OpenHarmony documentation and get an answer with citations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The question to ask"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of documents to retrieve (default: 6)",
                            "default": 6
                        },
                        "kit": {
                            "type": "string",
                            "description": "Filter by Kit (e.g., ArkUI, ArkTS)",
                            "optional": True
                        },
                        "top_dir": {
                            "type": "string",
                            "description": "Filter by top directory (e.g., application-dev, design)",
                            "optional": True
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "oh_docs_rag_retrieve",
                "description": "Search OpenHarmony documentation and retrieve relevant chunks without generating an answer",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 10)",
                            "default": 10
                        },
                        "kit": {
                            "type": "string",
                            "description": "Filter by Kit (e.g., ArkUI, ArkTS)",
                            "optional": True
                        },
                        "top_dir": {
                            "type": "string",
                            "description": "Filter by top directory (e.g., application-dev, design)",
                            "optional": True
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "oh_docs_rag_sync_repo",
                "description": "Sync the OpenHarmony documentation repository to get the latest updates",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "oh_docs_rag_stats",
                "description": "Get statistics about the indexed OpenHarmony documentation",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if tool_name == "oh_docs_rag_query":
            return await self._query(arguments)
        elif tool_name == "oh_docs_rag_retrieve":
            return await self._retrieve(arguments)
        elif tool_name == "oh_docs_rag_sync_repo":
            return await self._sync_repo()
        elif tool_name == "oh_docs_rag_stats":
            return await self._get_stats()
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query tool."""
        query = arguments.get("query")
        top_k = arguments.get("top_k", 6)
        kit = arguments.get("kit")
        top_dir = arguments.get("top_dir")

        filters = {}
        if kit:
            filters["kit"] = kit
        if top_dir:
            filters["top_dir"] = top_dir

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/query",
                json={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters if filters else None
                },
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()

        # Format result for MCP
        answer = result.get("answer", "")
        citations = result.get("citations", [])
        intent = result.get("intent", {})

        formatted_output = f"{answer}\n\n"

        if citations:
            formatted_output += "**参考文档：**\n"
            for i, citation in enumerate(citations, 1):
                formatted_output += f"{i}. [{citation['title']}]({citation['source_url']})\n"
                formatted_output += f"   路径: {citation['path']}\n"
                formatted_output += f"   片段: {citation['snippet']}\n\n"

        formatted_output += f"*意图: {intent.get('type', 'unknown')} (置信度: {intent.get('confidence', 0):.2f})*\n"
        formatted_output += f"*使用文档块数: {result.get('used_chunks', 0)}*\n"
        formatted_output += f"*延迟: {result.get('latency_ms', 0)}ms*"

        return {
            "content": [
                {
                    "type": "text",
                    "text": formatted_output
                }
            ]
        }

    async def _retrieve(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute retrieve tool."""
        query = arguments.get("query")
        top_k = arguments.get("top_k", 10)
        kit = arguments.get("kit")
        top_dir = arguments.get("top_dir")

        filters = {}
        if kit:
            filters["kit"] = kit
        if top_dir:
            filters["top_dir"] = top_dir

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/retrieve",
                json={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters if filters else None
                },
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        # Format result for MCP
        chunks = result.get("chunks", [])

        if not chunks:
            formatted_output = "未找到相关文档。"
        else:
            formatted_output = f"找到 {len(chunks)} 个相关文档片段：\n\n"

            for i, chunk in enumerate(chunks, 1):
                metadata = chunk.get("metadata", {})
                formatted_output += f"**{i}. {metadata.get('title', '未知标题')}**\n"
                formatted_output += f"路径: {metadata.get('path', '未知路径')}\n"
                formatted_output += f"标题路径: {chunk.get('heading_path', '')}\n"
                formatted_output += f"Kit: {metadata.get('kit', 'N/A')}\n"
                formatted_output += f"文档类型: {metadata.get('page_kind', 'unknown')}\n"
                formatted_output += f"相关度: {chunk.get('score', 0):.2f}\n"
                formatted_output += f"内容:\n{chunk.get('text', '')[:300]}...\n\n"

        return {
            "content": [
                {
                    "type": "text",
                    "text": formatted_output
                }
            ]
        }

    async def _sync_repo(self) -> Dict[str, Any]:
        """Execute sync_repo tool."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/sync-repo",
                headers=self.headers,
                timeout=300.0
            )
            response.raise_for_status()
            result = response.json()

        formatted_output = f"**仓库同步完成**\n\n"
        formatted_output += f"状态: {result.get('status', 'unknown')}\n"
        formatted_output += f"消息: {result.get('message', '')}\n"
        formatted_output += f"仓库路径: {result.get('repo_path', '')}\n"
        formatted_output += f"文件总数: {result.get('total_files', 0)}"

        return {
            "content": [
                {
                    "type": "text",
                    "text": formatted_output
                }
            ]
        }

    async def _get_stats(self) -> Dict[str, Any]:
        """Execute stats tool."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/stats",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            result = response.json()

        formatted_output = "**OpenHarmony 文档 RAG 系统统计**\n\n"
        formatted_output += f"文档总数: {result.get('total_documents', 0)}\n\n"

        formatted_output += "**按目录分布：**\n"
        for dir_name, count in result.get('by_top_dir', {}).items():
            formatted_output += f"  - {dir_name}: {count}\n"

        formatted_output += "\n**按 Kit 分布（Top 10）：**\n"
        for kit, count in result.get('by_kit', {}).items():
            formatted_output += f"  - {kit}: {count}\n"

        formatted_output += "\n**按文档类型分布：**\n"
        for kind, count in result.get('by_page_kind', {}).items():
            formatted_output += f"  - {kind}: {count}\n"

        formatted_output += "\n**文档类型标记：**\n"
        doc_types = result.get('document_types', {})
        formatted_output += f"  - API 参考: {doc_types.get('api_reference', 0)}\n"
        formatted_output += f"  - 开发指南: {doc_types.get('guide', 0)}\n"
        formatted_output += f"  - 设计规范: {doc_types.get('design_spec', 0)}"

        return {
            "content": [
                {
                    "type": "text",
                    "text": formatted_output
                }
            ]
        }


# Example usage
async def main():
    """Example usage of the MCP server."""
    mcp = OpenHarmonyDocsRAGMCP()

    # List available tools
    print("Available MCP Tools:")
    for tool in mcp.get_tools():
        print(f"  - {tool['name']}: {tool['description']}")

    print("\n" + "=" * 60 + "\n")

    # Call query tool
    print("Calling oh_docs_rag_query...")
    result = await mcp.call_tool(
        "oh_docs_rag_query",
        {"query": "如何创建 UIAbility 组件？", "top_k": 6}
    )
    print(result["content"][0]["text"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
