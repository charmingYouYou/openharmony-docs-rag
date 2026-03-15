"""Heading-aware chunking module for Markdown documents."""

import re
import hashlib
from typing import List, Tuple
from markdown_it import MarkdownIt

from app.schemas import ParsedDocument, Chunk, PageKind
from app.settings import Settings, settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HeadingAwareChunker:
    """Chunker that respects document structure and heading hierarchy."""

    version = "2026-03-14-table-split-v2"

    def __init__(
        self,
        target_size: int = None,
        overlap: int = None,
        settings_snapshot: Settings | None = None,
    ):
        """Bind chunk sizing to one optional runtime settings snapshot."""
        self.settings_snapshot = settings_snapshot or settings
        self.target_size = target_size or self.settings_snapshot.chunk_target_size
        self.overlap = overlap or self.settings_snapshot.chunk_overlap
        self.md = MarkdownIt()

    def chunk_document(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk document based on its type.

        Routes to specialized chunking methods based on document characteristics.
        """
        # Route to specialized chunkers
        if doc.is_api_reference:
            return self.chunk_api_reference(doc)
        elif doc.is_guide:
            return self.chunk_guide(doc)
        elif doc.is_design_spec:
            return self.chunk_design_spec(doc)
        elif doc.page_kind == PageKind.README:
            return self.chunk_readme(doc)
        else:
            return self.chunk_generic(doc)

    def chunk_api_reference(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk API reference documents.

        Strategy: Keep interface definitions complete, one interface per chunk.
        """
        chunks = []
        content = doc.content

        # Split by H2 or H3 headings (typically interface/method names)
        sections = self._split_by_headings(content, min_level=2, max_level=3)

        for idx, (heading_path, section_content) in enumerate(sections):
            # For API docs, keep the entire interface definition together
            # even if it exceeds target size
            if len(section_content) > self.target_size * 2:
                # If extremely long, split by code blocks
                sub_chunks = self._split_long_section(section_content, heading_path)
                for sub_content in sub_chunks:
                    chunk = self._create_chunk(
                        doc, sub_content, heading_path, len(chunks)
                    )
                    chunks.append(chunk)
            else:
                chunk = self._create_chunk(doc, section_content, heading_path, len(chunks))
                chunks.append(chunk)

        return chunks

    def chunk_guide(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk guide documents.

        Strategy: Keep steps coherent, avoid splitting in the middle of steps.
        """
        chunks = []
        content = doc.content

        # Split by H2 headings (major sections)
        sections = self._split_by_headings(content, min_level=2, max_level=2)

        for idx, (heading_path, section_content) in enumerate(sections):
            # Check if section contains numbered steps
            if self._contains_steps(section_content):
                # Keep steps together
                step_chunks = self._chunk_steps(section_content, heading_path)
                for step_content in step_chunks:
                    chunk = self._create_chunk(
                        doc, step_content, heading_path, len(chunks)
                    )
                    chunks.append(chunk)
            else:
                # Regular chunking with overlap
                sub_chunks = self._chunk_with_overlap(section_content)
                for sub_content in sub_chunks:
                    chunk = self._create_chunk(
                        doc, sub_content, heading_path, len(chunks)
                    )
                    chunks.append(chunk)

        return chunks

    def chunk_design_spec(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk design specification documents.

        Strategy: Keep design rules complete, one rule per chunk.
        """
        chunks = []
        content = doc.content

        # Split by H2 or H3 headings (design rules/guidelines)
        sections = self._split_by_headings(content, min_level=2, max_level=3)

        for idx, (heading_path, section_content) in enumerate(sections):
            # Keep design specs complete
            if len(section_content) > self.target_size * 1.5:
                sub_chunks = self._chunk_with_overlap(section_content)
                for sub_content in sub_chunks:
                    chunk = self._create_chunk(
                        doc, sub_content, heading_path, len(chunks)
                    )
                    chunks.append(chunk)
            else:
                chunk = self._create_chunk(doc, section_content, heading_path, len(chunks))
                chunks.append(chunk)

        return chunks

    def chunk_readme(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Chunk README documents.

        Strategy: Create fewer, larger chunks since READMEs are typically navigation.
        """
        chunks = []
        content = doc.content

        # Split by H2 headings only
        sections = self._split_by_headings(content, min_level=2, max_level=2)

        for idx, (heading_path, section_content) in enumerate(sections):
            chunk = self._create_chunk(doc, section_content, heading_path, len(chunks))
            chunks.append(chunk)

        return chunks

    def chunk_generic(self, doc: ParsedDocument) -> List[Chunk]:
        """
        Generic chunking for unknown document types.

        Strategy: Standard heading-aware chunking with overlap.
        """
        chunks = []
        content = doc.content

        sections = self._split_by_headings(content, min_level=2, max_level=3)

        for idx, (heading_path, section_content) in enumerate(sections):
            sub_chunks = self._chunk_with_overlap(section_content)
            for sub_content in sub_chunks:
                chunk = self._create_chunk(
                    doc, sub_content, heading_path, len(chunks)
                )
                chunks.append(chunk)

        return chunks

    def _split_by_headings(
        self, content: str, min_level: int = 2, max_level: int = 3
    ) -> List[Tuple[str, str]]:
        """
        Split content by heading levels.

        Returns list of (heading_path, content) tuples.
        """
        sections = []
        lines = content.split('\n')

        current_heading = "Document"
        current_content = []
        heading_stack = []

        for line in lines:
            # Check if line is a heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Save previous section
                if current_content and min_level <= len(heading_stack) <= max_level:
                    sections.append((current_heading, '\n'.join(current_content)))

                # Update heading stack
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))

                # Build heading path
                current_heading = ' > '.join([h[1] for h in heading_stack])
                current_content = [line]
            else:
                current_content.append(line)

        # Add last section
        if current_content:
            sections.append((current_heading, '\n'.join(current_content)))

        return sections

    def _chunk_with_overlap(self, content: str) -> List[str]:
        """Chunk content with overlap."""
        chunks = []
        chars = list(content)
        start = 0

        while start < len(chars):
            end = min(start + self.target_size, len(chars))
            chunk_text = ''.join(chars[start:end])
            chunks.append(chunk_text)

            if end >= len(chars):
                break

            start = end - self.overlap

        return chunks

    def _contains_steps(self, content: str) -> bool:
        """Check if content contains numbered steps."""
        return bool(re.search(r'(步骤\s*\d+|step\s*\d+|\d+\.\s+)', content, re.IGNORECASE))

    def _chunk_steps(self, content: str, heading_path: str) -> List[str]:
        """Chunk content by steps."""
        # Split by step markers
        step_pattern = r'((?:步骤\s*\d+|step\s*\d+|\d+\.\s+).+?)(?=(?:步骤\s*\d+|step\s*\d+|\d+\.\s+)|$)'
        steps = re.findall(step_pattern, content, re.IGNORECASE | re.DOTALL)

        if not steps:
            return [content]

        chunks = []
        current_chunk = ""

        for step in steps:
            if len(current_chunk) + len(step) <= self.target_size:
                current_chunk += step
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = step

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _split_long_section(self, content: str, heading_path: str) -> List[str]:
        """Split extremely long sections by code blocks or paragraphs."""
        # Try to split by code blocks first
        code_block_pattern = r'(```[\s\S]*?```)' 
        parts = re.split(code_block_pattern, content)

        chunks = []
        current_chunk = ""

        for part in parts:
            if len(current_chunk) + len(part) <= self.target_size * 1.5:
                current_chunk += part
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)

        return self._rebalance_oversized_chunks(chunks)

    def _rebalance_oversized_chunks(self, chunks: List[str]) -> List[str]:
        """Apply a final fallback split when code-block chunking still leaves huge chunks."""
        balanced_chunks = []
        max_chunk_size = self.target_size * 8

        for chunk in chunks:
            if len(chunk) <= max_chunk_size:
                balanced_chunks.append(chunk)
                continue

            balanced_chunks.extend(self._chunk_with_overlap(chunk))

        return balanced_chunks

    def _create_chunk(
        self, doc: ParsedDocument, text: str, heading_path: str, chunk_index: int
    ) -> Chunk:
        """Create a chunk object."""
        chunk_id = self._generate_chunk_id(doc.doc_id, chunk_index)

        metadata = {
            "path": doc.path,
            "title": doc.title,
            "top_dir": doc.top_dir,
            "sub_dir": doc.sub_dir,
            "page_kind": doc.page_kind.value,
            "kit": doc.metadata.kit,
            "subsystem": doc.metadata.subsystem,
            "is_api_reference": doc.is_api_reference,
            "is_guide": doc.is_guide,
            "is_design_spec": doc.is_design_spec,
        }

        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc.doc_id,
            text=text.strip(),
            heading_path=heading_path,
            chunk_index=chunk_index,
            metadata=metadata
        )

    def _generate_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Generate unique chunk ID as UUID."""
        import uuid
        combined = f"{doc_id}-{chunk_index}"
        # Generate UUID from MD5 hash to ensure consistency
        hash_bytes = hashlib.md5(combined.encode()).digest()
        return str(uuid.UUID(bytes=hash_bytes))
