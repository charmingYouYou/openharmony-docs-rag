"""
Skill Wrapper for OpenHarmony Docs RAG

This wrapper exposes the RAG system as a Claude Code Skill.
"""

import httpx
import json
from typing import Optional, Dict, Any


class OpenHarmonyDocsRAGSkill:
    """Skill wrapper for OpenHarmony documentation RAG system."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        """
        Initialize the skill.

        Args:
            api_base_url: Base URL of the RAG API
        """
        self.api_base_url = api_base_url
        self.headers = {"X-Caller-Type": "skill"}

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/retrieve",
                json={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters or {}
                },
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

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
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/query",
                json={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters or {}
                },
                headers=self.headers,
                timeout=60.0
            )
            response.raise_for_status()
            return response.json()

    async def sync_repository(self) -> Dict[str, Any]:
        """
        Sync OpenHarmony documentation repository.

        Returns:
            Sync status
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base_url}/sync-repo",
                headers=self.headers,
                timeout=300.0
            )
            response.raise_for_status()
            return response.json()

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get system statistics.

        Returns:
            Statistics about indexed documents
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base_url}/stats",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

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
