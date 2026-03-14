"""Runnable stdio MCP server for the OpenHarmony Docs RAG API."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from app.clients.rag_api_client import RAGAPIClient


def _build_filters(
    kit: str | None = None,
    top_dir: str | None = None,
) -> Optional[Dict[str, str]]:
    """Build API filters from optional MCP arguments."""
    filters = {}
    if kit:
        filters["kit"] = kit
    if top_dir:
        filters["top_dir"] = top_dir
    return filters or None


class OpenHarmonyDocsMCPService:
    """Tool implementation layer used by the stdio MCP server."""

    def __init__(
        self,
        api_base_url: str | None = None,
        client: RAGAPIClient | None = None,
    ):
        base_url = api_base_url or os.getenv(
            "OPENHARMONY_RAG_API_BASE_URL",
            "http://localhost:8000",
        )
        self.client = client or RAGAPIClient(base_url, caller_type="mcp")

    async def query(
        self,
        query: str,
        top_k: int = 6,
        kit: str | None = None,
        top_dir: str | None = None,
    ) -> Dict[str, Any]:
        """Ask a question about OpenHarmony docs and return the grounded answer payload."""
        return await self.client.query(
            query=query,
            top_k=top_k,
            filters=_build_filters(kit=kit, top_dir=top_dir),
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        kit: str | None = None,
        top_dir: str | None = None,
    ) -> Dict[str, Any]:
        """Retrieve relevant OpenHarmony doc chunks without generating an answer."""
        return await self.client.retrieve(
            query=query,
            top_k=top_k,
            filters=_build_filters(kit=kit, top_dir=top_dir),
        )

    async def sync_repo(self) -> Dict[str, Any]:
        """Sync the underlying OpenHarmony docs repository."""
        return await self.client.sync_repo()

    async def stats(self) -> Dict[str, Any]:
        """Return the current index statistics."""
        return await self.client.stats()


service = OpenHarmonyDocsMCPService()
mcp_server = FastMCP(
    "OpenHarmony Docs RAG",
    instructions=(
        "Use these tools to answer questions about OpenHarmony documentation with "
        "grounded retrieval from the local RAG API."
    ),
)


@mcp_server.tool(name="oh_docs_rag_query")
async def oh_docs_rag_query(
    query: str,
    top_k: int = 6,
    kit: str | None = None,
    top_dir: str | None = None,
) -> Dict[str, Any]:
    """Ask a question about OpenHarmony documentation and get an answer with citations."""
    return await service.query(query=query, top_k=top_k, kit=kit, top_dir=top_dir)


@mcp_server.tool(name="oh_docs_rag_retrieve")
async def oh_docs_rag_retrieve(
    query: str,
    top_k: int = 10,
    kit: str | None = None,
    top_dir: str | None = None,
) -> Dict[str, Any]:
    """Search OpenHarmony documentation and return relevant chunks only."""
    return await service.retrieve(query=query, top_k=top_k, kit=kit, top_dir=top_dir)


@mcp_server.tool(name="oh_docs_rag_sync_repo")
async def oh_docs_rag_sync_repo() -> Dict[str, Any]:
    """Sync the indexed OpenHarmony documentation repository."""
    return await service.sync_repo()


@mcp_server.tool(name="oh_docs_rag_stats")
async def oh_docs_rag_stats() -> Dict[str, Any]:
    """Get index statistics for the OpenHarmony documentation corpus."""
    return await service.stats()


def main():
    """Run the MCP server over stdio."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
