#!/usr/bin/env python3
"""Tests for the distributable skill wrapper."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill


class DummyClient:
    """Capture calls made by the skill wrapper."""

    def __init__(self):
        self.calls = []

    async def retrieve(self, query, top_k, filters=None):
        self.calls.append(("retrieve", query, top_k, filters))
        return {"chunks": [{"score": 0.9, "metadata": {"title": "ArkUI"}}]}

    async def query(self, query, top_k, filters=None):
        self.calls.append(("query", query, top_k, filters))
        return {"answer": "ok", "citations": [], "intent": {"type": "guide", "confidence": 0.8}}

    async def sync_repo(self):
        self.calls.append(("sync_repo",))
        return {"status": "success"}

    async def stats(self):
        self.calls.append(("stats",))
        return {"total_documents": 5299}


@pytest.mark.asyncio
async def test_skill_wrapper_delegates_to_shared_client():
    client = DummyClient()
    skill = OpenHarmonyDocsRAGSkill(client=client)

    retrieve_result = await skill.search_docs("ArkUI 组件", top_k=5, filters={"kit": "ArkUI"})
    query_result = await skill.ask_question("如何创建 UIAbility 组件？")
    stats_result = await skill.get_stats()

    assert retrieve_result["chunks"][0]["metadata"]["title"] == "ArkUI"
    assert query_result["answer"] == "ok"
    assert stats_result["total_documents"] == 5299
    assert client.calls == [
        ("retrieve", "ArkUI 组件", 5, {"kit": "ArkUI"}),
        ("query", "如何创建 UIAbility 组件？", 6, None),
        ("stats",),
    ]
