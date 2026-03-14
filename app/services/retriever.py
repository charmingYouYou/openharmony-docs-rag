"""Retrieval service with hybrid search and reranking."""

from typing import List, Optional

from app.schemas import (
    RetrievedChunk,
    RetrievalFilters,
    QueryIntent,
    PreprocessedQuery
)
from app.core.embedder import Embedder
from app.core.reranker import Reranker
from app.storage.qdrant_client import QdrantClient
from app.utils.query_preprocessor import QueryPreprocessor
from app.settings import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HybridRetriever:
    """Hybrid retrieval with intent-based boosting."""

    def __init__(self):
        self.embedder = Embedder()
        self.qdrant = QdrantClient()
        self.preprocessor = QueryPreprocessor()
        self.reranker = self._build_reranker()

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        filters: Optional[RetrievalFilters] = None,
        preprocessed_query: Optional[PreprocessedQuery] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve relevant chunks for query.

        Args:
            query: User query
            top_k: Number of results to return
            filters: Optional retrieval filters
            preprocessed_query: Optional preprocessed query (if already done)

        Returns:
            List of retrieved chunks with scores
        """
        # Preprocess query if not already done
        if not preprocessed_query:
            preprocessed_query = self.preprocessor.preprocess(query)

        logger.info(f"Query intent: {preprocessed_query.intent} (confidence: {preprocessed_query.confidence:.2f})")

        # Merge filters
        merged_filters = self._merge_filters(filters, preprocessed_query.filters)

        # Generate query embedding
        query_embedding = self.embedder.embed_text(preprocessed_query.normalized_query)

        # Search in Qdrant (retrieve more candidates when rerank is enabled)
        if self.reranker:
            search_top_k = max(top_k * 3, settings.rerank_top_k)
        else:
            search_top_k = min(top_k * 3, 30)
        results = self.qdrant.search(
            query_vector=query_embedding,
            top_k=search_top_k,
            filters=merged_filters
        )

        # Convert to RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id=result["chunk_id"],
                text=result["payload"]["text"],
                heading_path=result["payload"]["heading_path"],
                score=result["score"],
                metadata=self._extract_metadata(result["payload"])
            )
            for result in results
        ]

        if self.reranker:
            chunks = self.apply_rerank(
                query=preprocessed_query.normalized_query,
                chunks=chunks,
            )

        # Apply intent-based boosting
        chunks = self.apply_intent_boost(chunks, preprocessed_query.intent)

        # Sort by boosted score and return top_k
        chunks.sort(key=lambda x: x.score, reverse=True)
        return chunks[:top_k]

    def apply_rerank(self, query: str, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Apply second-stage reranking on recalled chunks."""
        if not self.reranker or not chunks:
            return chunks

        reranked = self.reranker.rerank(
            query=query,
            documents=[chunk.text for chunk in chunks],
            top_n=min(settings.rerank_top_k, len(chunks)),
        )

        reordered = []
        for item in reranked:
            index = item.get("index")
            if index is None or index < 0 or index >= len(chunks):
                continue
            chunk = chunks[index].model_copy(deep=True)
            chunk.score = item.get("relevance_score", chunk.score)
            reordered.append(chunk)

        if not reordered:
            return chunks

        return reordered

    def _build_reranker(self) -> Optional[Reranker]:
        """Create reranker only when fully configured."""
        if not settings.rerank_enabled:
            return None
        if not settings.rerank_is_configured:
            logger.warning("Rerank is enabled but configuration is incomplete; skipping reranker")
            return None
        return Reranker()

    def apply_intent_boost(
        self, chunks: List[RetrievedChunk], intent: QueryIntent
    ) -> List[RetrievedChunk]:
        """
        Apply intent-based score boosting.

        Args:
            chunks: List of retrieved chunks
            intent: Query intent

        Returns:
            Chunks with boosted scores
        """
        for chunk in chunks:
            boost = 1.0

            if intent == QueryIntent.GUIDE:
                # Boost guide documents
                if chunk.metadata.get("is_guide"):
                    boost = 1.3
                elif chunk.metadata.get("page_kind") == "guide":
                    boost = 1.2
                # Penalize readme
                if chunk.metadata.get("page_kind") == "readme":
                    boost = 0.7

            elif intent == QueryIntent.API_USAGE:
                # Boost API reference documents
                if chunk.metadata.get("is_api_reference"):
                    boost = 1.3
                elif chunk.metadata.get("page_kind") == "reference":
                    boost = 1.2
                # Boost if path contains /reference/
                if "/reference/" in chunk.metadata.get("path", ""):
                    boost *= 1.1

            elif intent == QueryIntent.DESIGN_SPEC:
                # Boost design spec documents
                if chunk.metadata.get("is_design_spec"):
                    boost = 1.3
                elif chunk.metadata.get("top_dir") == "design":
                    boost = 1.2

            elif intent == QueryIntent.CONCEPT:
                # Boost concept documents
                if chunk.metadata.get("page_kind") == "concept":
                    boost = 1.2

            # Apply boost
            chunk.score *= boost

        return chunks

    def _merge_filters(
        self,
        user_filters: Optional[RetrievalFilters],
        intent_filters: RetrievalFilters
    ) -> RetrievalFilters:
        """Merge user-provided filters with intent-based filters."""
        if not user_filters:
            return intent_filters

        # User filters take precedence
        merged = RetrievalFilters(
            top_dir=user_filters.top_dir or intent_filters.top_dir,
            kit=user_filters.kit or intent_filters.kit,
            subsystem=user_filters.subsystem or intent_filters.subsystem,
            page_kind=user_filters.page_kind or intent_filters.page_kind,
            exclude_readme=user_filters.exclude_readme or intent_filters.exclude_readme
        )

        return merged

    def _extract_metadata(self, payload: dict) -> dict:
        """Extract metadata from Qdrant payload."""
        return {
            "path": payload.get("path"),
            "title": payload.get("title"),
            "top_dir": payload.get("top_dir"),
            "sub_dir": payload.get("sub_dir"),
            "page_kind": payload.get("page_kind"),
            "kit": payload.get("kit"),
            "subsystem": payload.get("subsystem"),
            "is_api_reference": payload.get("is_api_reference", False),
            "is_guide": payload.get("is_guide", False),
            "is_design_spec": payload.get("is_design_spec", False),
        }
