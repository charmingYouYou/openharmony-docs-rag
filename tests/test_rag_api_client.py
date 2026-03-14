#!/usr/bin/env python3
"""Tests for the shared RAG API client used by skill and MCP integrations."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.clients.rag_api_client import RAGAPIClient


class DummyResponse:
    """Small httpx response stand-in."""

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_query_uses_expected_url_headers_and_payload(monkeypatch):
    captured = {}

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers, timeout):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            captured["timeout"] = timeout
            return DummyResponse({"answer": "ok"})

    monkeypatch.setattr("app.clients.rag_api_client.httpx.AsyncClient", DummyAsyncClient)

    result = await RAGAPIClient(
        api_base_url="http://127.0.0.1:8000/",
        caller_type="mcp",
    ).query(
        query="如何创建 UIAbility 组件？",
        top_k=6,
        filters={"kit": "ArkUI"},
    )

    assert result == {"answer": "ok"}
    assert captured["url"] == "http://127.0.0.1:8000/query"
    assert captured["json"] == {
        "query": "如何创建 UIAbility 组件？",
        "top_k": 6,
        "filters": {"kit": "ArkUI"},
    }
    assert captured["headers"] == {"X-Caller-Type": "mcp"}
    assert captured["timeout"] == 60.0


@pytest.mark.asyncio
async def test_stats_uses_get(monkeypatch):
    captured = {}

    class DummyAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return DummyResponse({"total_documents": 5299})

    monkeypatch.setattr("app.clients.rag_api_client.httpx.AsyncClient", DummyAsyncClient)

    result = await RAGAPIClient(
        api_base_url="http://127.0.0.1:8000",
        caller_type="skill",
    ).stats()

    assert result == {"total_documents": 5299}
    assert captured["url"] == "http://127.0.0.1:8000/stats"
    assert captured["headers"] == {"X-Caller-Type": "skill"}
    assert captured["timeout"] == 10.0
