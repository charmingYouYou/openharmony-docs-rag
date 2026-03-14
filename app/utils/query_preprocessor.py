"""Query preprocessing and intent recognition."""

import re
from typing import Tuple

from app.schemas import (
    PreprocessedQuery,
    QueryIntent,
    RetrievalFilters,
    PageKind
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryPreprocessor:
    """Preprocess queries and identify intent."""

    def __init__(self):
        # Intent patterns
        self.guide_patterns = [
            r'如何', r'怎么', r'怎样', r'指南', r'教程', r'快速入门',
            r'最佳实践', r'步骤', r'开始', r'创建',
            r'how to', r'guide', r'tutorial', r'quick start', r'getting started'
        ]

        self.api_patterns = [
            r'api', r'接口', r'方法', r'函数', r'参数', r'返回值',
            r'调用', r'使用.*api', r'interface', r'method', r'function'
        ]

        self.design_patterns = [
            r'设计规范', r'设计指南', r'ux', r'ui设计', r'组件设计',
            r'design spec', r'design guide', r'ux guide'
        ]

        self.concept_patterns = [
            r'是什么', r'什么是', r'概念', r'定义', r'介绍', r'概述',
            r'区别', r'对比',
            r'what is', r'concept', r'definition', r'overview', r'introduction'
        ]

    def preprocess(self, query: str) -> PreprocessedQuery:
        """
        Preprocess query and identify intent.

        Args:
            query: Raw user query

        Returns:
            PreprocessedQuery with normalized query, intent, and filters
        """
        # Normalize query
        normalized = self._normalize_query(query)

        # Identify intent
        intent, confidence = self._identify_intent(normalized)

        # Extract filters
        filters = self._extract_filters(normalized, intent)

        return PreprocessedQuery(
            normalized_query=normalized,
            intent=intent,
            confidence=confidence,
            filters=filters
        )

    def _normalize_query(self, query: str) -> str:
        """Normalize query text."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())

        # Normalize common terms
        normalized = normalized.replace('OpenHarmony', 'openharmony')

        return normalized

    def _identify_intent(self, query: str) -> Tuple[QueryIntent, float]:
        """
        Identify query intent.

        Returns:
            (intent, confidence_score)
        """
        query_lower = query.lower()

        # Check guide intent
        guide_score = sum(
            1 for pattern in self.guide_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )

        # Check API intent
        api_score = sum(
            1 for pattern in self.api_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )

        # Check design spec intent
        design_score = sum(
            1 for pattern in self.design_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )

        # Check concept intent
        concept_score = sum(
            1 for pattern in self.concept_patterns
            if re.search(pattern, query_lower, re.IGNORECASE)
        )

        # Determine intent based on scores
        scores = {
            QueryIntent.GUIDE: guide_score,
            QueryIntent.API_USAGE: api_score,
            QueryIntent.DESIGN_SPEC: design_score,
            QueryIntent.CONCEPT: concept_score
        }

        max_score = max(scores.values())

        if max_score == 0:
            return QueryIntent.GENERAL, 0.5

        # Get intent with highest score
        intent = max(scores, key=scores.get)

        # Calculate confidence (normalize to 0-1)
        confidence = min(max_score / 3.0, 1.0)

        return intent, confidence

    def _extract_filters(
        self, query: str, intent: QueryIntent
    ) -> RetrievalFilters:
        """Extract filters from query based on intent."""
        filters = RetrievalFilters()

        query_lower = query.lower()

        # Extract Kit name
        kit_match = re.search(r'(arkui|arkts|arkdata|arkgraphics|arkweb)', query_lower)
        if kit_match:
            filters.kit = kit_match.group(1).capitalize()

        # Set filters based on intent
        if intent == QueryIntent.GUIDE:
            filters.exclude_readme = True
            filters.page_kind = PageKind.GUIDE

        elif intent == QueryIntent.API_USAGE:
            filters.page_kind = PageKind.REFERENCE

        elif intent == QueryIntent.DESIGN_SPEC:
            filters.top_dir = "design"

        return filters
