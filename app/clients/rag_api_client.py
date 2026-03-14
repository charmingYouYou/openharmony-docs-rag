"""Shared async client for talking to the local OpenHarmony RAG API."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class RAGAPIClient:
    """Thin async wrapper around the RAG HTTP API."""

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        caller_type: str = "integration",
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.headers = {"X-Caller-Type": caller_type}

    async def query(
        self,
        query: str,
        top_k: int = 6,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call the /query endpoint."""
        return await self._post(
            "/query",
            {"query": query, "top_k": top_k, "filters": filters},
            timeout=60.0,
        )

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call the /retrieve endpoint."""
        return await self._post(
            "/retrieve",
            {"query": query, "top_k": top_k, "filters": filters},
            timeout=30.0,
        )

    async def sync_repo(self) -> Dict[str, Any]:
        """Call the /sync-repo endpoint."""
        return await self._post("/sync-repo", None, timeout=300.0)

    async def stats(self) -> Dict[str, Any]:
        """Call the /stats endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/stats",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def _post(
        self,
        path: str,
        payload: Optional[Dict[str, Any]],
        timeout: float,
    ) -> Dict[str, Any]:
        """POST JSON to one API endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}{path}",
                json=payload,
                headers=self.headers,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()
