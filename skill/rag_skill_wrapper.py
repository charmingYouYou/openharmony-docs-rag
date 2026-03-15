"""Thin Python wrapper for the query-only OpenHarmony Docs RAG skill."""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from app.clients.rag_api_client import RAGAPIClient


class OpenHarmonyDocsRAGSkill:
    """Expose the skill's query-only contract to Python callers."""

    def __init__(
        self,
        api_base_url: str | None = None,
        client: RAGAPIClient | None = None,
    ):
        """
        Initialize the skill.

        Args:
            api_base_url: Base URL of the RAG API
        """
        base_url = api_base_url or os.getenv(
            "OPENHARMONY_RAG_API_BASE_URL",
            "http://localhost:8000",
        )
        self.client = client or RAGAPIClient(base_url, caller_type="skill")

    async def ask_question(
        self,
        query: str,
        top_k: int = 6,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call the skill's only supported endpoint, `/query`, and return its payload."""
        return await self.client.query(query, top_k=top_k, filters=filters)

    def format_answer(self, result: Dict[str, Any]) -> str:
        """Format one `/query` response for CLI or notebook display."""
        answer = result.get("answer", "")
        citations = result.get("citations", [])
        intent = result.get("intent", {})

        output = f"{answer}\n\n"

        if citations:
            output += "**参考文档：**\n"
            for i, citation in enumerate(citations, 1):
                output += f"{i}. [{citation['title']}]({citation['source_url']})\n"
                output += f"   路径: {citation['path']}\n"

        output += f"\n*意图: {intent.get('type', 'unknown')} (置信度: {intent.get('confidence', 0):.2f})*"

        return output


async def main():
    """Run one query-only example for local verification."""
    skill = OpenHarmonyDocsRAGSkill()

    print("问题: 如何创建 UIAbility 组件？")
    result = await skill.ask_question("如何创建 UIAbility 组件？")
    print(skill.format_answer(result))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
