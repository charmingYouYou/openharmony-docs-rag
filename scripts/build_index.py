#!/usr/bin/env python3
"""Script to build the document index."""

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.settings import Settings, settings
from app.core.parser import MarkdownParser
from app.core.chunker import HeadingAwareChunker
from app.core.embedder import Embedder
from app.storage.qdrant_client import QdrantClient
from app.storage.sqlite_client import SQLiteClient
from app.storage.models import DocumentModel
from app.schemas import ParsedDocument, Chunk
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
INDEX_SIGNATURE_VERSION = "2026-03-14-incremental-v1"


class IndexBuilder:
    """Build document index from OpenHarmony documentation."""

    def __init__(
        self,
        settings_snapshot: Settings | None = None,
        base_path: Path | None = None,
        parser: MarkdownParser | None = None,
        chunker: HeadingAwareChunker | None = None,
        embedder: Embedder | None = None,
        qdrant: QdrantClient | None = None,
        sqlite: SQLiteClient | None = None,
    ):
        """Bind indexing collaborators to one optional runtime settings snapshot."""
        self.settings_snapshot = settings_snapshot or settings
        self.parser = parser or MarkdownParser()
        self.chunker = chunker or HeadingAwareChunker(
            settings_snapshot=self.settings_snapshot
        )
        self.embedder = embedder or Embedder(settings_snapshot=self.settings_snapshot)
        self.qdrant = qdrant or QdrantClient(settings_snapshot=self.settings_snapshot)
        self.sqlite = sqlite or SQLiteClient(settings_snapshot=self.settings_snapshot)
        self.base_path = base_path or Path(self.settings_snapshot.docs_local_path)

    async def build(
        self,
        full_rebuild: bool = False,
        progress_callback: Optional[Callable[[Dict[str, object]], None]] = None,
        should_pause: Optional[Callable[[], bool]] = None,
    ):
        """Build the complete index."""
        logger.info("Starting index build process")

        # Initialize storage
        logger.info("Initializing storage...")
        await self.sqlite.initialize()

        if full_rebuild:
            logger.info("Clearing existing data for full rebuild...")
            await self.sqlite.clear_all()
            self.qdrant.clear_collection()

        # Collect markdown files
        logger.info("Collecting markdown files...")
        md_files = self._collect_markdown_files()
        logger.info(f"Found {len(md_files)} markdown files to process")
        self._report_progress(
            progress_callback,
            {
                "type": "collection_scanned",
                "total_docs": len(md_files),
            },
        )

        existing_docs_by_path: Dict[str, DocumentModel] = {}
        if not full_rebuild:
            existing_docs_by_path = {
                doc.path: doc for doc in await self.sqlite.get_all_documents()
            }
            await self._cleanup_stale_documents(existing_docs_by_path, md_files)

        indexed_docs = 0
        reindexed_docs = 0
        skipped_docs = 0
        failed_docs = 0
        total_chunks = 0
        embedded_batches = 0
        collection_initialized = False
        current_path = ""

        for idx, md_file in enumerate(md_files, 1):
            parsed_doc = None
            doc_model = None
            try:
                if should_pause and should_pause():
                    return self._build_summary(
                        status="paused",
                        indexed_docs=indexed_docs,
                        reindexed_docs=reindexed_docs,
                        skipped_docs=skipped_docs,
                        failed_docs=failed_docs,
                        total_chunks=total_chunks,
                        total_docs=len(md_files),
                        current_path=current_path,
                    )

                logger.info(f"Processing [{idx}/{len(md_files)}]: {md_file.name}")

                # Parse document
                parsed_doc = self.parser.parse_file(md_file, self.base_path)
                if not parsed_doc:
                    logger.warning(f"Failed to parse {md_file}")
                    failed_docs += 1
                    continue

                current_path = parsed_doc.path
                self._report_progress(
                    progress_callback,
                    {
                        "type": "document_started",
                        "current_index": idx,
                        "processed_docs": indexed_docs
                        + reindexed_docs
                        + skipped_docs
                        + failed_docs,
                        "total_docs": len(md_files),
                        "path": parsed_doc.path,
                    },
                )

                # Chunk document
                chunks = self.chunker.chunk_document(parsed_doc)
                logger.info(f"Generated {len(chunks)} chunks")

                content_hash = self._content_hash(parsed_doc.content)
                index_signature = self._index_signature()
                existing_doc = existing_docs_by_path.get(parsed_doc.path)

                if self._should_skip_document(
                    existing_doc,
                    content_hash,
                    index_signature,
                    len(chunks),
                ):
                    skipped_docs += 1
                    logger.info(
                        f"Skipping unchanged indexed document: {parsed_doc.path}"
                    )
                    continue

                if existing_doc:
                    self._safe_delete_document_vectors(parsed_doc.doc_id)

                doc_model = self._create_document_model(
                    parsed_doc,
                    len(chunks),
                    content_hash=content_hash,
                    index_signature=index_signature,
                    index_status="indexing",
                    indexed_chunk_count=0,
                    last_error=None,
                    last_indexed_at=None,
                )
                await self.sqlite.insert_document(doc_model)

                if not chunks:
                    doc_model.index_status = "ready"
                    doc_model.last_indexed_at = datetime.now()
                    await self.sqlite.insert_document(doc_model)
                    existing_docs_by_path[parsed_doc.path] = doc_model
                    if existing_doc:
                        reindexed_docs += 1
                    else:
                        indexed_docs += 1
                    continue

                collection_initialized, embedded_batches, paused = await self._index_document(
                    doc_model,
                    chunks,
                    collection_initialized,
                    embedded_batches,
                    should_pause=should_pause,
                )
                if paused:
                    return self._build_summary(
                        status="paused",
                        indexed_docs=indexed_docs,
                        reindexed_docs=reindexed_docs,
                        skipped_docs=skipped_docs,
                        failed_docs=failed_docs,
                        total_chunks=total_chunks,
                        total_docs=len(md_files),
                        current_path=current_path,
                    )

                total_chunks += len(chunks)
                existing_docs_by_path[parsed_doc.path] = doc_model
                if existing_doc:
                    reindexed_docs += 1
                else:
                    indexed_docs += 1

                if idx % 100 == 0:
                    logger.info(
                        f"Processed {idx}/{len(md_files)} documents, indexed {indexed_docs + reindexed_docs}, skipped {skipped_docs}"
                    )

            except Exception as e:
                if parsed_doc is not None:
                    self._safe_delete_document_vectors(parsed_doc.doc_id)
                if doc_model is not None:
                    doc_model.index_status = "failed"
                    doc_model.indexed_chunk_count = 0
                    doc_model.last_error = str(e)
                    doc_model.last_indexed_at = None
                    await self.sqlite.insert_document(doc_model)
                logger.error(f"Failed to process {md_file}: {e}")
                failed_docs += 1
                continue

        # Summary
        logger.info("=" * 60)
        logger.info("Index build completed!")
        logger.info(f"Indexed documents: {indexed_docs}")
        logger.info(f"Reindexed documents: {reindexed_docs}")
        logger.info(f"Skipped documents: {skipped_docs}")
        logger.info(f"Indexed chunks this run: {total_chunks}")
        logger.info(f"Failed documents: {failed_docs}")
        logger.info(f"Qdrant points: {self.qdrant.count_points()}")
        logger.info(f"SQLite documents: {await self.sqlite.count_documents()}")
        logger.info("=" * 60)
        return self._build_summary(
            status="completed",
            indexed_docs=indexed_docs,
            reindexed_docs=reindexed_docs,
            skipped_docs=skipped_docs,
            failed_docs=failed_docs,
            total_chunks=total_chunks,
            total_docs=len(md_files),
            current_path=current_path,
        )

    def _collect_markdown_files(self) -> List[Path]:
        """Collect all markdown files from included directories."""
        md_files = []
        settings_snapshot = self._runtime_settings()

        for dir_name in settings_snapshot.include_dirs_list:
            target_dir = self.base_path / dir_name
            if not target_dir.exists():
                logger.warning(f"Directory does not exist: {target_dir}")
                continue

            # Find all .md files
            files = list(target_dir.rglob("*.md"))
            logger.info(f"Found {len(files)} files in {dir_name}")
            md_files.extend(files)

        return md_files

    async def _index_document(
        self,
        doc_model: DocumentModel,
        chunks: List[Chunk],
        collection_initialized: bool,
        embedded_batches: int,
        should_pause: Optional[Callable[[], bool]] = None,
    ) -> tuple[bool, int, bool]:
        """Index one document end-to-end so failures do not poison later documents."""
        pending_doc_models = {doc_model.doc_id: doc_model}
        remaining_chunks_by_doc = {doc_model.doc_id: len(chunks)}
        batch_size = self._runtime_settings().embedding_batch_size

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start:start + batch_size]
            embedded_batches = self._maybe_wait_between_batches(embedded_batches)
            logger.info(
                f"Embedding batch {embedded_batches + 1} ({len(batch)} chunks)"
            )

            if start + len(batch) >= len(chunks):
                doc_model.index_status = "ready"
                doc_model.indexed_chunk_count = len(chunks)
                doc_model.last_error = None
                doc_model.last_indexed_at = datetime.now()

            collection_initialized = await self._flush_chunk_batch(
                batch,
                pending_doc_models,
                remaining_chunks_by_doc,
                collection_initialized,
            )
            embedded_batches += 1
            has_more_batches = start + len(batch) < len(chunks)
            if has_more_batches and should_pause and should_pause():
                return collection_initialized, embedded_batches, True

        return collection_initialized, embedded_batches, False

    async def _cleanup_stale_documents(
        self,
        existing_docs_by_path: Dict[str, DocumentModel],
        md_files: List[Path],
    ):
        """Delete documents whose source files no longer exist."""
        current_paths = {
            str(file_path.relative_to(self.base_path))
            for file_path in md_files
        }
        stale_paths = [
            path for path in existing_docs_by_path.keys() if path not in current_paths
        ]

        for stale_path in stale_paths:
            doc = existing_docs_by_path.pop(stale_path)
            self._safe_delete_document_vectors(doc.doc_id)
            await self.sqlite.delete_document(doc.doc_id)
            logger.info(f"Removed stale indexed document: {stale_path}")

    def _should_skip_document(
        self,
        existing_doc: DocumentModel | None,
        content_hash: str,
        index_signature: str,
        chunk_count: int,
    ) -> bool:
        """Check whether a document is already indexed for the current configuration."""
        if not existing_doc:
            return False

        return (
            existing_doc.index_status == "ready"
            and existing_doc.content_hash == content_hash
            and existing_doc.index_signature == index_signature
            and existing_doc.chunk_count == chunk_count
            and existing_doc.indexed_chunk_count == chunk_count
        )

    def _content_hash(self, content: str) -> str:
        """Hash raw Markdown content for incremental invalidation."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _index_signature(self) -> str:
        """Hash indexing-relevant settings so model/chunker changes trigger reindex."""
        settings_snapshot = self._runtime_settings()
        payload = {
            "version": INDEX_SIGNATURE_VERSION,
            "embedding_base_url": settings_snapshot.embedding_base_url,
            "embedding_model": settings_snapshot.embedding_model,
            "document_input_type": settings_snapshot.embedding_document_input_type,
            "document_prefix": settings_snapshot.embedding_document_prefix,
            "chunk_target_size": settings_snapshot.chunk_target_size,
            "chunk_overlap": settings_snapshot.chunk_overlap,
            "parser_version": getattr(self.parser, "version", "v1"),
            "chunker_version": getattr(self.chunker, "version", "v1"),
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.md5(encoded).hexdigest()

    async def _flush_chunk_batch(
        self,
        chunks: List[Chunk],
        pending_doc_models: Dict[str, DocumentModel],
        remaining_chunks_by_doc: Dict[str, int],
        collection_initialized: bool,
    ) -> bool:
        """Embed and write one chunk batch, then flush any completed documents."""
        if not chunks:
            return collection_initialized

        embeddings = self.embedder.embed_batch([chunk.text for chunk in chunks])
        if len(embeddings) != len(chunks):
            raise ValueError(
                f"Embedding count mismatch: expected {len(chunks)}, got {len(embeddings)}"
            )

        if not collection_initialized:
            vector_size = len(embeddings[0])
            logger.info("Ensuring Qdrant collection matches detected vector size...")
            get_vector_size = getattr(self.qdrant, "get_vector_size", None)
            existing_vector_size = get_vector_size() if callable(get_vector_size) else None
            if (
                existing_vector_size is not None
                and existing_vector_size != vector_size
            ):
                logger.warning(
                    "Existing Qdrant collection vector size "
                    f"{existing_vector_size} does not match current embedding size "
                    f"{vector_size}; clearing collection before continuing"
                )
                self.qdrant.clear_collection()
            self.qdrant.initialize_collection(vector_size=vector_size)
            collection_initialized = True

        self.qdrant.insert_chunks(chunks, embeddings)

        for chunk in chunks:
            remaining_chunks_by_doc[chunk.doc_id] -= 1
            if remaining_chunks_by_doc[chunk.doc_id] != 0:
                continue

            await self.sqlite.insert_document(pending_doc_models.pop(chunk.doc_id))
            del remaining_chunks_by_doc[chunk.doc_id]

        return collection_initialized

    def _maybe_wait_between_batches(self, embedded_batches: int) -> int:
        """Sleep between embedding batches when configured."""
        settings_snapshot = self._runtime_settings()
        if embedded_batches and settings_snapshot.embedding_inter_batch_delay_seconds > 0:
            logger.info(
                "Sleeping "
                f"{settings_snapshot.embedding_inter_batch_delay_seconds}s before next embedding batch"
            )
            time.sleep(settings_snapshot.embedding_inter_batch_delay_seconds)
        return embedded_batches

    def _safe_delete_document_vectors(self, doc_id: str):
        """Delete prior vectors for a document and ignore missing-collection cases."""
        try:
            self.qdrant.delete_by_doc_id(doc_id)
        except Exception as exc:
            logger.warning(f"Failed to delete vectors for {doc_id}: {exc}")

    def _create_document_model(
        self,
        parsed_doc: ParsedDocument,
        chunk_count: int,
        content_hash: str | None = None,
        index_signature: str | None = None,
        index_status: str = "ready",
        indexed_chunk_count: int = 0,
        last_error: str | None = None,
        last_indexed_at: datetime | None = None,
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
            indexed_chunk_count=indexed_chunk_count,
            content_hash=content_hash,
            index_signature=index_signature,
            index_status=index_status,
            last_error=last_error,
            last_indexed_at=last_indexed_at,
        )

    def _generate_source_url(self, rel_path: str) -> str:
        """Generate Gitee source URL for document."""
        base_url = "https://gitee.com/openharmony/docs/blob/master"
        return f"{base_url}/{rel_path}"

    def _report_progress(
        self,
        progress_callback: Optional[Callable[[Dict[str, object]], None]],
        payload: Dict[str, object],
    ):
        """Emit one structured progress payload when a callback is provided."""
        if progress_callback is None:
            return
        progress_callback(payload)

    def _runtime_settings(self) -> Settings:
        """Return the bound settings snapshot or fall back to the latest process settings."""
        return getattr(self, "settings_snapshot", None) or settings

    def _build_summary(
        self,
        status: str,
        indexed_docs: int,
        reindexed_docs: int,
        skipped_docs: int,
        failed_docs: int,
        total_chunks: int,
        total_docs: int,
        current_path: str,
    ) -> Dict[str, object]:
        """Return a structured summary for CLI callers and web orchestration."""
        return {
            "status": status,
            "processed_docs": indexed_docs + reindexed_docs + skipped_docs + failed_docs,
            "indexed_docs": indexed_docs,
            "reindexed_docs": reindexed_docs,
            "skipped_docs": skipped_docs,
            "failed_docs": failed_docs,
            "total_chunks": total_chunks,
            "total_docs": total_docs,
            "current_path": current_path,
        }


def parse_args():
    """Parse build-index CLI arguments."""
    parser = argparse.ArgumentParser(description="Build the OpenHarmony docs index")
    parser.add_argument(
        "--full-rebuild",
        action="store_true",
        help="Clear SQLite and Qdrant before indexing instead of running incrementally.",
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()
    builder = IndexBuilder()
    await builder.build(full_rebuild=args.full_rebuild)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Build interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Build failed: {e}")
        sys.exit(1)
