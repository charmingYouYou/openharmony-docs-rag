#!/usr/bin/env python3
"""Regression tests for retrieval orchestration."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.services.retriever as retriever_module
from app.schemas import PreprocessedQuery, QueryIntent, RetrievalFilters
from app.services.retriever import HybridRetriever


def make_preprocessed(intent=QueryIntent.API_USAGE):
    return PreprocessedQuery(
        normalized_query="router.pushUrl 方法如何使用？",
        intent=intent,
        confidence=1.0,
        filters=RetrievalFilters(),
    )


def test_retrieve_uses_reranker_scores_when_available():
    retriever = HybridRetriever.__new__(HybridRetriever)

    class DummyEmbedder:
        def embed_text(self, text):
            return [0.1, 0.2]

    class DummyQdrant:
        def search(self, query_vector, top_k, filters):
            return [
                {
                    "chunk_id": "chunk-a",
                    "score": 0.95,
                    "payload": {
                        "text": "deprecated router docs",
                        "heading_path": "A",
                        "path": "a.md",
                        "page_kind": "reference",
                        "is_api_reference": True,
                    },
                },
                {
                    "chunk_id": "chunk-b",
                    "score": 0.80,
                    "payload": {
                        "text": "new UIContext router docs",
                        "heading_path": "B",
                        "path": "b.md",
                        "page_kind": "reference",
                        "is_api_reference": True,
                    },
                },
            ]

    class DummyPreprocessor:
        def preprocess(self, query):
            return make_preprocessed()

    class DummyReranker:
        def __init__(self):
            self.calls = []

        def rerank(self, query, documents, top_n=None):
            self.calls.append(
                {
                    "query": query,
                    "documents": documents,
                    "top_n": top_n,
                }
            )
            return [
                {"index": 1, "relevance_score": 0.99},
                {"index": 0, "relevance_score": 0.40},
            ]

    retriever.embedder = DummyEmbedder()
    retriever.qdrant = DummyQdrant()
    retriever.preprocessor = DummyPreprocessor()
    retriever.reranker = DummyReranker()

    results = retriever.retrieve("router.pushUrl 方法如何使用？", top_k=2)

    assert [item.chunk_id for item in results] == ["chunk-b", "chunk-a"]
    assert [round(item.score, 2) for item in results] == [1.29, 0.52]
    assert retriever.reranker.calls == [
        {
            "query": "router.pushUrl 方法如何使用？",
            "documents": ["deprecated router docs", "new UIContext router docs"],
            "top_n": 2,
        }
    ]


def test_retrieve_falls_back_to_dense_scores_without_reranker():
    retriever = HybridRetriever.__new__(HybridRetriever)

    class DummyEmbedder:
        def embed_text(self, text):
            return [0.1]

    class DummyQdrant:
        def search(self, query_vector, top_k, filters):
            return [
                {
                    "chunk_id": "chunk-a",
                    "score": 0.5,
                    "payload": {
                        "text": "guide text",
                        "heading_path": "A",
                        "path": "a.md",
                        "page_kind": "guide",
                        "is_guide": True,
                    },
                }
            ]

    class DummyPreprocessor:
        def preprocess(self, query):
            return make_preprocessed(intent=QueryIntent.GUIDE)

    retriever.embedder = DummyEmbedder()
    retriever.qdrant = DummyQdrant()
    retriever.preprocessor = DummyPreprocessor()
    retriever.reranker = None

    results = retriever.retrieve("如何创建 UIAbility 组件？", top_k=1)

    assert [item.chunk_id for item in results] == ["chunk-a"]
    assert round(results[0].score, 2) == 0.65


def test_build_reranker_accepts_embedding_config_fallback(monkeypatch):
    retriever = HybridRetriever.__new__(HybridRetriever)
    sentinel = object()

    monkeypatch.setattr(retriever_module.settings, "rerank_enabled", True)
    monkeypatch.setattr(retriever_module.settings, "rerank_model", "Qwen/Qwen3-Reranker-4B")
    monkeypatch.setattr(retriever_module.settings, "rerank_api_key", "")
    monkeypatch.setattr(retriever_module.settings, "rerank_base_url", "")
    monkeypatch.setattr(retriever_module.settings, "embedding_api_key", "embed-key")
    monkeypatch.setattr(
        retriever_module.settings,
        "embedding_base_url",
        "https://api.siliconflow.cn",
    )
    monkeypatch.setattr(retriever_module, "Reranker", lambda: sentinel)

    assert retriever._build_reranker() is sentinel
