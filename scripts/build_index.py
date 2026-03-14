#!/usr/bin/env python3
"""Script to build the document index."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import settings
from app.core.parser import MarkdownParser
from app.core.chunker import HeadingAwareChunker
from app.core.embedder import Embedder
from app.storage.qdrant_client import QdrantClient
from app.storage.sqlite_client import SQLiteClient
from app.storage.models import DocumentModel
from app.schemas import ParsedDocument, Chunk
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class IndexBuilder:
    """Build document index from OpenHarmony documentation."""

    def __init__(self):
        self.parser = MarkdownParser()
        self.chunker = HeadingAwareChunker()
        self.embedder = Embedder()
        self.qdrant = QdrantClient()
        self.sqlite = SQLiteClient()
        self.base_path = Path(settings.docs_local_path)

    async def build(self):
        """Build the complete index."""
        logger.info("Starting index build process")

        # Initialize storage
        logger.info("Initializing storage...")
        await self.sqlite.initialize()
        self.qdrant.initialize_collection()

        # Clear existing data
        logger.info("Clearing existing data...")
        await self.sqlite.clear_all()
        self.qdrant.clear_collection()
        self.qdrant.initialize_collection()

        # Collect markdown files
        logger.info("Collecting markdown files...")
        md_files = self._collect_markdown_files()
        logger.info(f"Found {len(md_files)} markdown files to process")

        # Process documents
        total_chunks = 0
        processed_docs = 0
        failed_docs = 0

        for idx, md_file in enumerate(md_files, 1):
            try:
                logger.info(f"Processing [{idx}/{len(md_files)}]: {md_file.name}")

                # Parse document
                parsed_doc = self.parser.parse_file(md_file, self.base_path)
                if not parsed_doc:
                    logger.warning(f"Failed to parse {md_file}")
                    failed_docs += 1
                    continue

                # Chunk document
                chunks = self.chunker.chunk_document(parsed_doc)
                if not chunks:
                    logger.warning(f"No chunks generated for {md_file}")
                    continue

                logger.info(f"Generated {len(chunks)} chunks")

                # Generate embeddings
                texts = [chunk.text for chunk in chunks]
                embeddings = self.embedder.embed_batch(texts)

                # Insert into Qdrant
                self.qdrant.insert_chunks(chunks, embeddings)

                # Insert metadata into SQLite
                doc_model = self._create_document_model(parsed_doc, len(chunks))
                await self.sqlite.insert_document(doc_model)

                total_chunks += len(chunks)
                processed_docs += 1

                if idx % 10 == 0:
                    logger.info(f"Progress: {idx}/{len(md_files)} documents, {total_chunks} chunks")

            except Exception as e:
                logger.error(f"Failed to process {md_file}: {e}")
                failed_docs += 1
                continue

        # Summary
        logger.info("=" * 60)
        logger.info("Index build completed!")
        logger.info(f"Total documents processed: {processed_docs}")
        logger.info(f"Total chunks created: {total_chunks}")
        logger.info(f"Failed documents: {failed_docs}")
        logger.info(f"Qdrant points: {self.qdrant.count_points()}")
        logger.info(f"SQLite documents: {await self.sqlite.count_documents()}")
        logger.info("=" * 60)

    def _collect_markdown_files(self) -> List[Path]:
        """Collect all markdown files from included directories."""
        md_files = []

        for dir_name in settings.include_dirs_list:
            target_dir = self.base_path / dir_name
            if not target_dir.exists():
                logger.warning(f"Directory does not exist: {target_dir}")
                continue

            # Find all .md files
            files = list(target_dir.rglob("*.md"))
            logger.info(f"Found {len(files)} files in {dir_name}")
            md_files.extend(files)

        return md_files

    def _create_document_model(
        self, parsed_doc: ParsedDocument, chunk_count: int
    ) -> DocumentModel:
        """Create DocumentModel from ParsedDocument."""
        # Generate source URL
        source_url = self._generate_source_url(parsed_doc.path)

        return DocumentModel(
            doc_id=parsed_doc.doc_id,
            path=parsed_doc.path,
            title=parsed_doc.title,
            source_url=source_url,
            top_dir=parsed_doc.top_dir,
            sub_dir=parsed_doc.sub_dir,
            page_kind=parsed_doc.page_kind.value,
            kit=parsed_doc.metadata.kit,
            subsystem=parsed_doc.metadata.subsystem,
            owner=parsed_doc.metadata.owner,
            is_api_reference=parsed_doc.is_api_reference,
            is_guide=parsed_doc.is_guide,
            is_design_spec=parsed_doc.is_design_spec,
            chunk_count=chunk_count,
            last_indexed_at=datetime.now()
        )

    def _generate_source_url(self, rel_path: str) -> str:
        """Generate Gitee source URL for document."""
        base_url = "https://gitee.com/openharmony/docs/blob/master"
        return f"{base_url}/{rel_path}"


async def main():
    """Main entry point."""
    builder = IndexBuilder()
    await builder.build()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)
