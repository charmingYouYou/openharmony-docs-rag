#!/usr/bin/env python3
"""Tests for the MCP tool service layer."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_mcp.stdio_server import OpenHarmonyDocsMCPService


class DummyClient:
    """Capture calls made by MCP tools."""

    def __init__(self):
        self.calls = []

    async def query(self, query, top_k, filters=None):
        self.calls.append(("query", query, top_k, filters))
        return {"answer": "ok"}

    async def retrieve(self, query, top_k, filters=None):
        self.calls.append(("retrieve", query, top_k, filters))
        return {"chunks": []}

    async def sync_repo(self):
        self.calls.append(("sync_repo",))
        return {"status": "success"}

    async def stats(self):
        self.calls.append(("stats",))
        return {"total_documents": 5299}


@pytest.mark.asyncio
async def test_mcp_service_builds_filters_and_returns_api_payload():
    client = DummyClient()
    service = OpenHarmonyDocsMCPService(client=client)

    query_result = await service.query(
        query="router.pushUrl 方法如何使用？",
        top_k=4,
        kit="ArkUI",
        top_dir="application-dev",
    )
    retrieve_result = await service.retrieve("ArkUI 组件", top_k=3)

    assert query_result == {"answer": "ok"}
    assert retrieve_result == {"chunks": []}
    assert client.calls == [
        (
            "query",
            "router.pushUrl 方法如何使用？",
            4,
            {"kit": "ArkUI", "top_dir": "application-dev"},
        ),
        ("retrieve", "ArkUI 组件", 3, None),
    ]


def test_skill_manifest_exists_and_mentions_api_base_env():
    manifest = Path(__file__).parent.parent / "skill" / "SKILL.md"

    assert manifest.exists()
    content = manifest.read_text(encoding="utf-8")
    assert "OPENHARMONY_RAG_API_BASE_URL" in content
    assert "query" in content
