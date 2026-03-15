#!/usr/bin/env python3
"""Tests for the query-only distributable skill wrapper."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from skill.rag_skill_wrapper import OpenHarmonyDocsRAGSkill


class DummyClient:
    """Capture `/query` calls made by the skill wrapper."""

    def __init__(self):
        self.calls = []

    async def query(self, query, top_k, filters=None):
        self.calls.append(("query", query, top_k, filters))
        return {
            "answer": "ok",
            "citations": [
                {
                    "title": "UIAbility",
                    "source_url": "https://example.test/uiability",
                    "path": "zh-cn/application-dev/ui/uiability.md",
                }
            ],
            "intent": {"type": "guide", "confidence": 0.8},
        }


@pytest.mark.asyncio
async def test_skill_wrapper_only_delegates_query_calls():
    client = DummyClient()
    skill = OpenHarmonyDocsRAGSkill(client=client)

    query_result = await skill.ask_question(
        "如何创建 UIAbility 组件？",
        filters={"kit": "Ability Kit"},
    )
    formatted = skill.format_answer(query_result)

    assert query_result["answer"] == "ok"
    assert "UIAbility" in formatted
    assert "guide" in formatted
    assert client.calls == [
        ("query", "如何创建 UIAbility 组件？", 6, {"kit": "Ability Kit"}),
    ]
