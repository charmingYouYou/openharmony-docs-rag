"""Distributable skill wrapper for the OpenHarmony Docs RAG API."""

from __future__ import annotations

import os
from typing import Optional, Dict, Any

from app.clients.rag_api_client import RAGAPIClient


class OpenHarmonyDocsRAGSkill:
    """Skill wrapper for OpenHarmony documentation RAG system."""

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

    async def search_docs(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search OpenHarmony documentation.

        Args:
            query: Search query
            top_k: Number of results to return
            filters: Optional filters (top_dir, kit, page_kind, etc.)

        Returns:
            Search results with chunks
        """
        return await self.client.retrieve(query, top_k=top_k, filters=filters)

    async def ask_question(
        self,
        query: str,
        top_k: int = 6,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ask a question about OpenHarmony documentation.

        Args:
            query: Question to ask
            top_k: Number of documents to retrieve
            filters: Optional filters (top_dir, kit, page_kind, etc.)

        Returns:
            Answer with citations
        """
        return await self.client.query(query, top_k=top_k, filters=filters)

    async def sync_repository(self) -> Dict[str, Any]:
        """
        Sync OpenHarmony documentation repository.

        Returns:
            Sync status
        """
        return await self.client.sync_repo()

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.

        Returns:
            Statistics about indexed documents
        """
        return await self.client.stats()

    def format_answer(self, result: Dict[str, Any]) -> str:
        """
        Format answer result for display.

        Args:
            result: Result from ask_question

        Returns:
            Formatted answer string
        """
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

    def format_search_results(self, result: Dict[str, Any]) -> str:
        """
        Format search results for display.

        Args:
            result: Result from search_docs

        Returns:
            Formatted search results string
        """
        chunks = result.get("chunks", [])

        if not chunks:
            return "未找到相关文档。"

        output = f"找到 {len(chunks)} 个相关文档片段：\n\n"

        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            output += f"**{i}. {metadata.get('title', '未知标题')}**\n"
            output += f"路径: {metadata.get('path', '未知路径')}\n"
            output += f"标题路径: {chunk.get('heading_path', '')}\n"
            output += f"相关度: {chunk.get('score', 0):.2f}\n"
            output += f"内容: {chunk.get('text', '')[:200]}...\n\n"

        return output


# Example usage
async def main():
    """Example usage of the skill."""
    skill = OpenHarmonyDocsRAGSkill()

    # Ask a question
    print("问题: 如何创建 UIAbility 组件？")
    result = await skill.ask_question("如何创建 UIAbility 组件？")
    print(skill.format_answer(result))

    print("\n" + "=" * 60 + "\n")

    # Search documents
    print("搜索: ArkUI 组件")
    result = await skill.search_docs("ArkUI 组件", top_k=5)
    print(skill.format_search_results(result))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
