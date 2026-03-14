#!/usr/bin/env python3
"""Regression tests for the configured embeddings flow."""

import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.embedder as embedder_module
import scripts.build_index as build_index_module


class FakeResponse:
    """Minimal requests.Response stand-in for tests."""

    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
        self.text = json.dumps(self._payload, ensure_ascii=False)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error


@pytest.fixture
def embedding_settings(monkeypatch):
    monkeypatch.setattr(embedder_module.settings, "embedding_api_key", "test-key")
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_base_url",
        "https://api.siliconflow.cn",
    )
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_model",
        "Qwen/Qwen3-Embedding-4B",
    )
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_document_input_type",
        "document",
    )
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_query_input_type",
        "query",
    )
    monkeypatch.setattr(embedder_module.settings, "embedding_max_retries", 1)
    monkeypatch.setattr(embedder_module.settings, "embedding_retry_backoff_seconds", 1.0)
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_document_prefix",
        "",
        raising=False,
    )
    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_query_prefix",
        "",
        raising=False,
    )


def test_embed_batch_uses_document_request_shape(embedding_settings, monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            },
        )

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    embeddings = embedder_module.Embedder().embed_batch(["doc-a", "doc-b"])

    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert captured["url"] == "https://api.siliconflow.cn/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {
        "model": "Qwen/Qwen3-Embedding-4B",
        "input": ["doc-a", "doc-b"],
        "input_type": "document",
    }
    assert captured["timeout"] == 60


def test_embed_text_uses_query_input_type(embedding_settings, monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return FakeResponse(200, {"data": [{"embedding": [1.0, 2.0, 3.0]}]})

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    embedding = embedder_module.Embedder().embed_text("如何创建 UIAbility？")

    assert embedding == [1.0, 2.0, 3.0]
    assert captured["json"]["input"] == ["如何创建 UIAbility？"]
    assert captured["json"]["input_type"] == "query"


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://api.siliconflow.cn", "https://api.siliconflow.cn/v1/embeddings"),
        ("https://api.siliconflow.cn/", "https://api.siliconflow.cn/v1/embeddings"),
        ("https://api.siliconflow.cn/v1", "https://api.siliconflow.cn/v1/embeddings"),
        (
            "https://api.siliconflow.cn/v1/embeddings",
            "https://api.siliconflow.cn/v1/embeddings",
        ),
    ],
)
def test_base_url_normalization(embedding_settings, monkeypatch, base_url, expected_url):
    monkeypatch.setattr(embedder_module.settings, "embedding_base_url", base_url)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        return FakeResponse(200, {"data": [{"embedding": [0.1]}]})

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    embedder_module.Embedder().embed_text("query")

    assert captured["url"] == expected_url


def test_embed_text_applies_query_prefix(embedding_settings, monkeypatch):
    captured = {}

    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_query_prefix",
        "Instruct: Retrieve OpenHarmony passages that answer the question\\nQuery: ",
        raising=False,
    )

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return FakeResponse(200, {"data": [{"embedding": [1.0, 2.0, 3.0]}]})

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    embedder_module.Embedder().embed_text("如何创建 UIAbility？")

    assert captured["json"]["input"] == [
        "Instruct: Retrieve OpenHarmony passages that answer the question\nQuery: 如何创建 UIAbility？"
    ]


def test_embed_batch_applies_document_prefix(embedding_settings, monkeypatch):
    captured = {}

    monkeypatch.setattr(
        embedder_module.settings,
        "embedding_document_prefix",
        "passage: ",
        raising=False,
    )

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return FakeResponse(
            200,
            {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            },
        )

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    embedder_module.Embedder().embed_batch(["doc-a", "doc-b"])

    assert captured["json"]["input"] == ["passage: doc-a", "passage: doc-b"]


def test_embed_batch_rejects_incomplete_response(embedding_settings, monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(200, {"data": [{"embedding": [0.1, 0.2]}]})

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)

    with pytest.raises(ValueError, match="expected 2 embeddings, got 1"):
        embedder_module.Embedder().embed_batch(["doc-a", "doc-b"])


def test_embed_batch_retries_after_429(embedding_settings, monkeypatch):
    responses = [
        FakeResponse(429, {"detail": "rate limit"}),
        FakeResponse(200, {"data": [{"embedding": [0.1, 0.2]}]}),
    ]
    sleep_calls = []

    def fake_post(url, headers, json, timeout):
        return responses.pop(0)

    monkeypatch.setattr(embedder_module.requests, "post", fake_post)
    monkeypatch.setattr(embedder_module.time, "sleep", sleep_calls.append)
    monkeypatch.setattr(embedder_module.settings, "embedding_max_retries", 2)
    monkeypatch.setattr(embedder_module.settings, "embedding_retry_backoff_seconds", 0.25)

    embedding = embedder_module.Embedder().embed_text("query")

    assert embedding == [0.1, 0.2]
    assert sleep_calls == [0.25]


@pytest.mark.asyncio
async def test_flush_chunk_batch_initializes_qdrant_once_and_inserts_completed_docs():
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    class DummyEmbedder:
        def embed_batch(self, texts):
            return [[float(index)] for index, _ in enumerate(texts, 1)]

    class DummyQdrant:
        def __init__(self):
            self.initialized = []
            self.inserted = []
            self.cleared = 0

        def get_vector_size(self):
            return None

        def clear_collection(self):
            self.cleared += 1

        def initialize_collection(self, vector_size):
            self.initialized.append(vector_size)

        def insert_chunks(self, chunks, embeddings):
            self.inserted.append(([chunk.chunk_id for chunk in chunks], embeddings))

    class DummySQLite:
        def __init__(self):
            self.inserted = []

        async def insert_document(self, doc):
            self.inserted.append(doc.doc_id)

    builder.embedder = DummyEmbedder()
    builder.qdrant = DummyQdrant()
    builder.sqlite = DummySQLite()

    pending_docs = {
        "doc-1": SimpleNamespace(doc_id="doc-1"),
        "doc-2": SimpleNamespace(doc_id="doc-2"),
    }
    remaining_chunks = {"doc-1": 2, "doc-2": 1}

    first_batch = [
        SimpleNamespace(chunk_id="chunk-1", doc_id="doc-1", text="a"),
        SimpleNamespace(chunk_id="chunk-2", doc_id="doc-1", text="b"),
    ]
    second_batch = [
        SimpleNamespace(chunk_id="chunk-3", doc_id="doc-2", text="c"),
    ]

    collection_ready = await builder._flush_chunk_batch(
        first_batch,
        pending_docs,
        remaining_chunks,
        collection_initialized=False,
    )

    assert collection_ready is True
    assert builder.qdrant.initialized == [1]
    assert builder.qdrant.cleared == 0
    assert builder.sqlite.inserted == ["doc-1"]
    assert "doc-1" not in pending_docs
    assert remaining_chunks == {"doc-2": 1}

    collection_ready = await builder._flush_chunk_batch(
        second_batch,
        pending_docs,
        remaining_chunks,
        collection_initialized=collection_ready,
    )

    assert collection_ready is True
    assert builder.qdrant.initialized == [1]
    assert builder.sqlite.inserted == ["doc-1", "doc-2"]
    assert pending_docs == {}
    assert remaining_chunks == {}


@pytest.mark.asyncio
async def test_flush_chunk_batch_resets_qdrant_when_vector_size_changes():
    builder = build_index_module.IndexBuilder.__new__(build_index_module.IndexBuilder)

    class DummyEmbedder:
        def embed_batch(self, texts):
            return [[0.1, 0.2] for _ in texts]

    class DummyQdrant:
        def __init__(self):
            self.initialized = []
            self.inserted = []
            self.cleared = 0

        def get_vector_size(self):
            return 1

        def clear_collection(self):
            self.cleared += 1

        def initialize_collection(self, vector_size):
            self.initialized.append(vector_size)

        def insert_chunks(self, chunks, embeddings):
            self.inserted.append(([chunk.chunk_id for chunk in chunks], embeddings))

    class DummySQLite:
        def __init__(self):
            self.inserted = []

        async def insert_document(self, doc):
            self.inserted.append(doc.doc_id)

    builder.embedder = DummyEmbedder()
    builder.qdrant = DummyQdrant()
    builder.sqlite = DummySQLite()

    pending_docs = {"doc-1": SimpleNamespace(doc_id="doc-1")}
    remaining_chunks = {"doc-1": 1}
    batch = [SimpleNamespace(chunk_id="chunk-1", doc_id="doc-1", text="a")]

    collection_ready = await builder._flush_chunk_batch(
        batch,
        pending_docs,
        remaining_chunks,
        collection_initialized=False,
    )

    assert collection_ready is True
    assert builder.qdrant.cleared == 1
    assert builder.qdrant.initialized == [2]
    assert builder.sqlite.inserted == ["doc-1"]
