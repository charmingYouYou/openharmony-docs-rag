#!/usr/bin/env python3
"""Regression tests for incremental indexing and resume behavior."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import Chunk, DocumentMetadata, PageKind, ParsedDocument
from app.storage.models import DocumentModel
from app.storage.sqlite_client import SQLiteClient
import scripts.build_index as build_index_module


def make_parsed_doc(path: str, content: str = "# Doc\n\ncontent") -> ParsedDocument:
    return ParsedDocument(
        doc_id="doc-1",
        path=path,
        title="Doc",
        content=content,
        metadata=DocumentMetadata(),
        page_kind=PageKind.GUIDE,
        is_api_reference=False,
        is_guide=True,
        is_design_spec=False,
        top_dir="application-dev",
        sub_dir="guide",
    )


def make_chunks(doc_id: str) -> list[Chunk]:
    return [
        Chunk(
            chunk_id=f"{doc_id}-chunk-1",
            doc_id=doc_id,
            text="chunk one",
            heading_path="Doc",
            chunk_index=0,
            metadata={"path": "zh-cn/application-dev/doc.md"},
        ),
        Chunk(
            chunk_id=f"{doc_id}-chunk-2",
            doc_id=doc_id,
            text="chunk two",
            heading_path="Doc",
            chunk_index=1,
            metadata={"path": "zh-cn/application-dev/doc.md"},
        ),
    ]


@pytest.mark.asyncio
async def test_sqlite_roundtrip_preserves_incremental_indexing_fields(tmp_path):
    client = SQLiteClient(str(tmp_path / "index.db"))
    await client.initialize()

    doc = DocumentModel(
        doc_id="doc-1",
        path="zh-cn/application-dev/doc.md",
        title="Doc",
        chunk_count=2,
        indexed_chunk_count=2,
        content_hash="content-hash",
        index_signature="signature-hash",
        index_status="ready",
        last_error=None,
    )
    await client.insert_document(doc)

    stored = await client.get_document("doc-1")

    assert stored.content_hash == "content-hash"
    assert stored.index_signature == "signature-hash"
    assert stored.index_status == "ready"
    assert stored.indexed_chunk_count == 2


@pytest.mark.asyncio
async def test_incremental_build_skips_ready_unchanged_document(monkeypatch):
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    parsed_doc = make_parsed_doc("zh-cn/application-dev/doc.md")
    chunks = make_chunks(parsed_doc.doc_id)

    class FakeParser:
        def parse_file(self, file_path, base_path):
            return parsed_doc

    class FakeChunker:
        version = "chunker-v1"

        def chunk_document(self, doc):
            return chunks

    class FakeEmbedder:
        def __init__(self):
            self.calls = []

        def embed_batch(self, texts):
            self.calls.append(texts)
            return [[0.1], [0.2]]

    class FakeQdrant:
        def __init__(self):
            self.deleted = []
            self.inserted = []
            self.cleared = 0

        def clear_collection(self):
            self.cleared += 1

        def delete_by_doc_id(self, doc_id):
            self.deleted.append(doc_id)

        def initialize_collection(self, vector_size):
            pass

        def insert_chunks(self, chunks, embeddings):
            self.inserted.append((chunks, embeddings))

        def count_points(self):
            return 0

    class FakeSQLite:
        def __init__(self):
            self.clear_all_calls = 0
            self.inserted = []

        async def initialize(self):
            return None

        async def clear_all(self):
            self.clear_all_calls += 1

        async def get_all_documents(self):
            return [
                DocumentModel(
                    doc_id="doc-1",
                    path="zh-cn/application-dev/doc.md",
                    chunk_count=2,
                    indexed_chunk_count=2,
                    content_hash="same-hash",
                    index_signature="same-signature",
                    index_status="ready",
                )
            ]

        async def insert_document(self, doc):
            self.inserted.append(doc)

        async def delete_document(self, doc_id):
            return None

        async def count_documents(self):
            return 1

    builder.parser = FakeParser()
    builder.chunker = FakeChunker()
    builder.embedder = FakeEmbedder()
    builder.qdrant = FakeQdrant()
    builder.sqlite = FakeSQLite()
    builder.base_path = Path("/tmp/docs")
    builder._collect_markdown_files = lambda: [builder.base_path / parsed_doc.path]

    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_content_hash",
        lambda self, content: "same-hash",
    )
    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_index_signature",
        lambda self: "same-signature",
    )

    await builder.build(full_rebuild=False)

    assert builder.sqlite.clear_all_calls == 0
    assert builder.embedder.calls == []
    assert builder.qdrant.deleted == []
    assert builder.qdrant.inserted == []
    assert builder.sqlite.inserted == []


@pytest.mark.asyncio
async def test_incremental_build_reindexes_changed_document(monkeypatch):
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    parsed_doc = make_parsed_doc("zh-cn/application-dev/doc.md", content="# Doc\n\nnew")
    chunks = make_chunks(parsed_doc.doc_id)

    class FakeParser:
        def parse_file(self, file_path, base_path):
            return parsed_doc

    class FakeChunker:
        version = "chunker-v1"

        def chunk_document(self, doc):
            return chunks

    class FakeEmbedder:
        def __init__(self):
            self.calls = []

        def embed_batch(self, texts):
            self.calls.append(texts)
            return [[0.1], [0.2]]

    class FakeQdrant:
        def __init__(self):
            self.deleted = []
            self.inserted = []
            self.cleared = 0
            self.vector_sizes = []

        def clear_collection(self):
            self.cleared += 1

        def delete_by_doc_id(self, doc_id):
            self.deleted.append(doc_id)

        def initialize_collection(self, vector_size):
            self.vector_sizes.append(vector_size)

        def insert_chunks(self, chunks, embeddings):
            self.inserted.append((chunks, embeddings))

        def count_points(self):
            return 2

    class FakeSQLite:
        def __init__(self):
            self.inserted = []

        async def initialize(self):
            return None

        async def clear_all(self):
            raise AssertionError("incremental mode should not clear metadata")

        async def get_all_documents(self):
            return [
                DocumentModel(
                    doc_id="doc-1",
                    path="zh-cn/application-dev/doc.md",
                    chunk_count=2,
                    indexed_chunk_count=2,
                    content_hash="old-hash",
                    index_signature="same-signature",
                    index_status="ready",
                )
            ]

        async def insert_document(self, doc):
            self.inserted.append(doc)

        async def delete_document(self, doc_id):
            return None

        async def count_documents(self):
            return 1

    builder.parser = FakeParser()
    builder.chunker = FakeChunker()
    builder.embedder = FakeEmbedder()
    builder.qdrant = FakeQdrant()
    builder.sqlite = FakeSQLite()
    builder.base_path = Path("/tmp/docs")
    builder._collect_markdown_files = lambda: [builder.base_path / parsed_doc.path]

    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_content_hash",
        lambda self, content: "new-hash",
    )
    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_index_signature",
        lambda self: "same-signature",
    )

    await builder.build(full_rebuild=False)

    assert builder.qdrant.deleted == ["doc-1"]
    assert builder.embedder.calls == [["chunk one", "chunk two"]]
    assert builder.qdrant.vector_sizes == [1]
    assert builder.sqlite.inserted[-1].index_status == "ready"
    assert builder.sqlite.inserted[-1].indexed_chunk_count == 2
    assert builder.sqlite.inserted[-1].content_hash == "new-hash"


@pytest.mark.asyncio
async def test_incremental_build_marks_failed_document_and_cleans_partial_vectors(monkeypatch):
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    parsed_doc = make_parsed_doc("zh-cn/application-dev/doc.md")
    chunks = make_chunks(parsed_doc.doc_id)

    class FakeParser:
        def parse_file(self, file_path, base_path):
            return parsed_doc

    class FakeChunker:
        version = "chunker-v1"

        def chunk_document(self, doc):
            return chunks

    class FakeEmbedder:
        def embed_batch(self, texts):
            raise RuntimeError("embedding failed")

    class FakeQdrant:
        def __init__(self):
            self.deleted = []

        def clear_collection(self):
            return None

        def delete_by_doc_id(self, doc_id):
            self.deleted.append(doc_id)

        def initialize_collection(self, vector_size):
            raise AssertionError("should not initialize collection on failed embed")

        def insert_chunks(self, chunks, embeddings):
            raise AssertionError("should not insert on failed embed")

        def count_points(self):
            return 0

    class FakeSQLite:
        def __init__(self):
            self.inserted = []

        async def initialize(self):
            return None

        async def clear_all(self):
            return None

        async def get_all_documents(self):
            return []

        async def insert_document(self, doc):
            self.inserted.append(doc)

        async def delete_document(self, doc_id):
            return None

        async def count_documents(self):
            return len(self.inserted)

    builder.parser = FakeParser()
    builder.chunker = FakeChunker()
    builder.embedder = FakeEmbedder()
    builder.qdrant = FakeQdrant()
    builder.sqlite = FakeSQLite()
    builder.base_path = Path("/tmp/docs")
    builder._collect_markdown_files = lambda: [builder.base_path / parsed_doc.path]

    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_content_hash",
        lambda self, content: "content-hash",
    )
    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_index_signature",
        lambda self: "signature-hash",
    )

    await builder.build(full_rebuild=False)

    assert builder.qdrant.deleted == ["doc-1"]
    assert builder.sqlite.inserted[-1].index_status == "failed"
    assert builder.sqlite.inserted[-1].last_error == "embedding failed"
    assert builder.sqlite.inserted[-1].indexed_chunk_count == 0


@pytest.mark.asyncio
async def test_full_rebuild_clears_storage_before_processing(monkeypatch):
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    parsed_doc = make_parsed_doc("zh-cn/application-dev/doc.md")

    class FakeParser:
        def parse_file(self, file_path, base_path):
            return parsed_doc

    class FakeChunker:
        version = "chunker-v1"

        def chunk_document(self, doc):
            return [make_chunks(parsed_doc.doc_id)[0]]

    class FakeEmbedder:
        def embed_batch(self, texts):
            return [[0.1]]

    class FakeQdrant:
        def __init__(self):
            self.cleared = 0

        def clear_collection(self):
            self.cleared += 1

        def delete_by_doc_id(self, doc_id):
            return None

        def initialize_collection(self, vector_size):
            return None

        def insert_chunks(self, chunks, embeddings):
            return None

        def count_points(self):
            return 1

    class FakeSQLite:
        def __init__(self):
            self.clear_all_calls = 0
            self.inserted = []

        async def initialize(self):
            return None

        async def clear_all(self):
            self.clear_all_calls += 1

        async def get_all_documents(self):
            return []

        async def insert_document(self, doc):
            self.inserted.append(doc)

        async def delete_document(self, doc_id):
            return None

        async def count_documents(self):
            return 1

    builder.parser = FakeParser()
    builder.chunker = FakeChunker()
    builder.embedder = FakeEmbedder()
    builder.qdrant = FakeQdrant()
    builder.sqlite = FakeSQLite()
    builder.base_path = Path("/tmp/docs")
    builder._collect_markdown_files = lambda: [builder.base_path / parsed_doc.path]

    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_content_hash",
        lambda self, content: "content-hash",
    )
    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_index_signature",
        lambda self: "signature-hash",
    )

    await builder.build(full_rebuild=True)

    assert builder.sqlite.clear_all_calls == 1
    assert builder.qdrant.cleared == 1


@pytest.mark.asyncio
async def test_incremental_build_can_pause_safely_between_batches(monkeypatch):
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    parsed_doc = make_parsed_doc("zh-cn/application-dev/doc.md", content="# Doc\n\npause me")
    chunks = make_chunks(parsed_doc.doc_id)

    class FakeParser:
        def parse_file(self, file_path, base_path):
            return parsed_doc

    class FakeChunker:
        version = "chunker-v1"

        def chunk_document(self, doc):
            return chunks

    class FakeEmbedder:
        def __init__(self):
            self.calls = []

        def embed_batch(self, texts):
            self.calls.append(list(texts))
            return [[0.1] for _ in texts]

    class FakeQdrant:
        def __init__(self):
            self.inserted = []

        def clear_collection(self):
            return None

        def delete_by_doc_id(self, doc_id):
            return None

        def initialize_collection(self, vector_size):
            return None

        def insert_chunks(self, chunks, embeddings):
            self.inserted.append([chunk.chunk_id for chunk in chunks])

        def count_points(self):
            return sum(len(batch) for batch in self.inserted)

    class FakeSQLite:
        def __init__(self):
            self.inserted = []

        async def initialize(self):
            return None

        async def clear_all(self):
            return None

        async def get_all_documents(self):
            return []

        async def insert_document(self, doc):
            self.inserted.append(doc)

        async def delete_document(self, doc_id):
            return None

        async def count_documents(self):
            return len(self.inserted)

    builder.parser = FakeParser()
    builder.chunker = FakeChunker()
    builder.embedder = FakeEmbedder()
    builder.qdrant = FakeQdrant()
    builder.sqlite = FakeSQLite()
    builder.base_path = Path("/tmp/docs")
    builder._collect_markdown_files = lambda: [builder.base_path / parsed_doc.path]

    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_content_hash",
        lambda self, content: "content-hash",
    )
    monkeypatch.setattr(
        build_index_module.IndexBuilder,
        "_index_signature",
        lambda self: "signature-hash",
    )
    monkeypatch.setattr(build_index_module.settings, "embedding_batch_size", 1)

    pause_checks = iter([False, True])
    summary = await builder.build(
        full_rebuild=False,
        should_pause=lambda: next(pause_checks, True),
    )

    assert summary["status"] == "paused"
    assert summary["processed_docs"] == 0
    assert builder.embedder.calls == [["chunk one"]]
    assert builder.qdrant.inserted == [["doc-1-chunk-1"]]
    assert builder.sqlite.inserted[0].index_status == "indexing"
