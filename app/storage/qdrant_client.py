"""Qdrant vector store client."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from qdrant_client import QdrantClient as QdrantClientSDK
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest
)

from app.schemas import Chunk, RetrievalFilters
from app.settings import Settings, settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class QdrantClient:
    """Qdrant vector store client."""

    def __init__(
        self,
        settings_snapshot: Settings | None = None,
        collection_name: str | None = None,
    ):
        """Bind Qdrant access to one optional runtime settings snapshot and collection."""
        self.settings_snapshot = settings_snapshot or settings
        self.client = QdrantClientSDK(
            host=self.settings_snapshot.qdrant_host,
            port=self.settings_snapshot.qdrant_port
        )
        self.collection_name = collection_name or self.settings_snapshot.qdrant_collection

    def initialize_collection(self, vector_size: int):
        """
        Initialize Qdrant collection.

        Args:
            vector_size: Dimension of embedding vectors
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name in collection_names:
                logger.info(f"Collection {self.collection_name} already exists")
                return

            # Create collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Collection {self.collection_name} created successfully")

        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            raise

    def get_vector_size(self) -> Optional[int]:
        """Return the configured vector size for the collection, if it exists."""
        try:
            collections = self.client.get_collections().collections
            collection_names = [collection.name for collection in collections]
            if self.collection_name not in collection_names:
                return None

            collection = self.client.get_collection(collection_name=self.collection_name)
            vectors_config = collection.config.params.vectors
            if isinstance(vectors_config, dict):
                first_vector = next(iter(vectors_config.values()), None)
                return getattr(first_vector, "size", None)
            return getattr(vectors_config, "size", None)
        except Exception as e:
            logger.warning(f"Failed to inspect collection vector size: {e}")
            return None

    def insert_chunks(self, chunks: List[Chunk], embeddings: List[List[float]]):
        """
        Insert chunks with embeddings into Qdrant.

        Args:
            chunks: List of chunks
            embeddings: List of embedding vectors
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks and embeddings must match")

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "text": chunk.text,
                "heading_path": chunk.heading_path,
                "chunk_index": chunk.chunk_index,
                "indexed_at": datetime.now().isoformat(),
                **chunk.metadata
            }

            point = PointStruct(
                id=chunk.chunk_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)

        # Insert in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            logger.info(f"Inserted batch {i // batch_size + 1} ({len(batch)} chunks)")

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[RetrievalFilters] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters

        Returns:
            List of search results with scores and payloads
        """
        # Build filter conditions
        filter_conditions = self._build_filter(filters) if filters else None

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=filter_conditions
        )

        return [
            {
                "chunk_id": result.id,
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]

    def delete_by_doc_id(self, doc_id: str):
        """Delete all chunks for a document."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        )
        logger.info(f"Deleted chunks for document {doc_id}")

    def clear_collection(self):
        """Clear all data from collection."""
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Collection {self.collection_name} deleted")
        except Exception as e:
            logger.warning(f"Failed to delete collection: {e}")

    def count_points(self) -> int:
        """Count total points in collection."""
        try:
            result = self.client.count(
                collection_name=self.collection_name,
                exact=True,
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count points: {e}")
            return 0

    def _build_filter(self, filters: RetrievalFilters) -> Filter:
        """Build Qdrant filter from RetrievalFilters."""
        conditions = []
        excluded_conditions = []

        if filters.top_dir:
            conditions.append(
                FieldCondition(
                    key="top_dir",
                    match=MatchValue(value=filters.top_dir)
                )
            )

        if filters.kit:
            conditions.append(
                FieldCondition(
                    key="kit",
                    match=MatchValue(value=filters.kit)
                )
            )

        if filters.subsystem:
            conditions.append(
                FieldCondition(
                    key="subsystem",
                    match=MatchValue(value=filters.subsystem)
                )
            )

        if filters.page_kind:
            conditions.append(
                FieldCondition(
                    key="page_kind",
                    match=MatchValue(value=filters.page_kind.value)
                )
            )

        if filters.exclude_readme:
            excluded_conditions.append(
                FieldCondition(
                    key="page_kind",
                    match=MatchValue(value="readme"),
                )
            )

        if not conditions and not excluded_conditions:
            return None

        return Filter(
            must=conditions or None,
            must_not=excluded_conditions or None,
        )
