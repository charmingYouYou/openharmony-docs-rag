"""Citation builder utility."""

from typing import List

from app.schemas import Citation, RetrievedChunk
from app.settings import settings


class CitationBuilder:
    """Build citations from retrieved chunks."""

    def build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """
        Build citations from retrieved chunks.

        Args:
            chunks: List of retrieved chunks

        Returns:
            List of citations
        """
        citations = []

        for chunk in chunks:
            # Extract snippet (first 200 chars)
            snippet = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text

            # Generate source URL
            source_url = self._generate_source_url(chunk.metadata.get("path", ""))

            citation = Citation(
                path=chunk.metadata.get("path", ""),
                title=chunk.metadata.get("title"),
                heading_path=chunk.heading_path,
                snippet=snippet,
                source_url=source_url
            )
            citations.append(citation)

        return citations

    def _generate_source_url(self, rel_path: str) -> str:
        """Generate Gitee source URL for document."""
        base_url = "https://gitee.com/openharmony/docs/blob/master"
        return f"{base_url}/{rel_path}"
