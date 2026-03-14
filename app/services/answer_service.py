"""Answer generation service with LLM."""

from typing import List, Dict
from openai import OpenAI

from app.schemas import (
    RetrievedChunk,
    QueryIntent,
    Citation
)
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AnswerService:
    """Generate answers using LLM based on retrieved context."""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )
        self.model = settings.llm_chat_model

    def generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        intent: QueryIntent
    ) -> str:
        """
        Generate answer based on retrieved chunks.

        Args:
            query: User query
            chunks: Retrieved document chunks
            intent: Query intent

        Returns:
            Generated answer
        """
        # Build prompt based on intent
        system_prompt = self._build_system_prompt(intent)
        context = self._build_context(chunks)
        user_prompt = self._build_user_prompt(query, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )

            answer = response.choices[0].message.content
            logger.info(f"Generated answer with {len(answer)} characters")
            return answer

        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise

    def _build_system_prompt(self, intent: QueryIntent) -> str:
        """Build system prompt based on intent."""
        base_prompt = """你是 OpenHarmony 开发文档助手。你的任务是基于提供的文档内容回答用户问题。

通用规则：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，明确告知用户
3. 使用清晰、专业的语言
4. 保持回答简洁，重点突出
5. 如果文档中有代码示例，优先展示
"""

        intent_specific = {
            QueryIntent.GUIDE: """
特别注意（指南类问题）：
- 优先引导用户查看官方指南和快速入门文档
- 如果有多个实现方式，说明推荐方案和理由
- 提供清晰的步骤说明和注意事项
- 引用相关的最佳实践和常见问题
- 如果文档中有代码示例，优先展示
""",
            QueryIntent.API_USAGE: """
特别注意（API 使用类问题）：
- 准确说明接口定义、参数、返回值
- 提供完整的代码示例
- 说明使用注意事项和常见错误
- 引用官方 API 参考文档路径
- 如果有版本差异，说明清楚
""",
            QueryIntent.DESIGN_SPEC: """
特别注意（设计规范类问题）：
- 准确引用官方设计规范和 UX 指南
- 说明设计原则和最佳实践
- 如果有组件设计规范，提供具体要求
- 引用相关的设计文档路径
""",
            QueryIntent.CONCEPT: """
特别注意（概念类问题）：
- 清晰解释概念定义
- 如果涉及对比，说明关键区别
- 提供实际应用场景
- 引用相关的概念说明文档
""",
            QueryIntent.GENERAL: """
特别注意（通用问题）：
- 根据文档内容提供准确回答
- 如果问题涉及多个方面，分点说明
- 引用相关文档路径
"""
        }

        return base_prompt + intent_specific.get(intent, intent_specific[QueryIntent.GENERAL])

    def _build_context(self, chunks: List[RetrievedChunk]) -> str:
        """Build context from retrieved chunks."""
        context_parts = []

        for idx, chunk in enumerate(chunks, 1):
            # Extract metadata
            path = chunk.metadata.get("path", "未知路径")
            heading = chunk.heading_path
            kit = chunk.metadata.get("kit", "")

            # Build context entry
            context_entry = f"""
【文档 {idx}】
路径: {path}
标题: {heading}
{f"Kit: {kit}" if kit else ""}

内容:
{chunk.text}
"""
            context_parts.append(context_entry.strip())

        return "\n\n---\n\n".join(context_parts)

    def _build_user_prompt(self, query: str, context: str) -> str:
        """Build user prompt with query and context."""
        return f"""基于以下文档内容回答问题。

文档内容：
{context}

---

用户问题：{query}

请基于上述文档内容回答用户问题。如果文档中没有相关信息，请明确告知。
"""

    def check_relevance(self, query: str, chunks: List[RetrievedChunk]) -> bool:
        """
        Check if retrieved chunks are relevant to the query.

        Returns:
            True if relevant, False if not
        """
        if not chunks:
            return False

        # Simple heuristic: check if top chunk has reasonable score
        top_score = chunks[0].score if chunks else 0
        return top_score > 0.5  # Threshold can be adjusted
