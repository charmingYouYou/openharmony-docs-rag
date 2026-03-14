#!/usr/bin/env python3
"""Regression tests for configured reranker flow."""

import json
from pathlib import Path
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

import app.core.reranker as reranker_module


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
def rerank_settings(monkeypatch):
    monkeypatch.setattr(reranker_module.settings, "rerank_enabled", True)
    monkeypatch.setattr(reranker_module.settings, "embedding_api_key", "embed-key")
    monkeypatch.setattr(
        reranker_module.settings,
        "embedding_base_url",
        "https://api.siliconflow.cn",
    )
    monkeypatch.setattr(reranker_module.settings, "rerank_api_key", "test-key")
    monkeypatch.setattr(
        reranker_module.settings,
        "rerank_base_url",
        "https://api.siliconflow.cn",
    )
    monkeypatch.setattr(
        reranker_module.settings,
        "rerank_model",
        "Qwen/Qwen3-Reranker-4B",
    )
    monkeypatch.setattr(reranker_module.settings, "rerank_top_k", 7)
    monkeypatch.setattr(reranker_module.settings, "rerank_max_retries", 2)
    monkeypatch.setattr(
        reranker_module.settings,
        "rerank_retry_backoff_seconds",
        1.0,
    )


def test_rerank_uses_expected_request_shape(rerank_settings, monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            {
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.4},
                ]
            },
        )

    monkeypatch.setattr(reranker_module.requests, "post", fake_post)

    results = reranker_module.Reranker().rerank(
        query="router.pushUrl 方法如何使用？",
        documents=["doc-a", "doc-b"],
        top_n=2,
    )

    assert results == [
        {"index": 1, "relevance_score": 0.9},
        {"index": 0, "relevance_score": 0.4},
    ]
    assert captured["url"] == "https://api.siliconflow.cn/v1/rerank"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {
        "model": "Qwen/Qwen3-Reranker-4B",
        "query": "router.pushUrl 方法如何使用？",
        "documents": ["doc-a", "doc-b"],
        "top_n": 2,
        "return_documents": False,
    }
    assert captured["timeout"] == 60


@pytest.mark.parametrize(
    ("base_url", "expected_url"),
    [
        ("https://api.siliconflow.cn", "https://api.siliconflow.cn/v1/rerank"),
        ("https://api.siliconflow.cn/", "https://api.siliconflow.cn/v1/rerank"),
        ("https://api.siliconflow.cn/v1", "https://api.siliconflow.cn/v1/rerank"),
        ("https://api.siliconflow.cn/v1/rerank", "https://api.siliconflow.cn/v1/rerank"),
    ],
)
def test_rerank_base_url_normalization(
    rerank_settings, monkeypatch, base_url, expected_url
):
    monkeypatch.setattr(reranker_module.settings, "rerank_base_url", base_url)

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        return FakeResponse(200, {"results": [{"index": 0, "relevance_score": 1.0}]})

    monkeypatch.setattr(reranker_module.requests, "post", fake_post)

    reranker_module.Reranker().rerank("query", ["doc"])

    assert captured["url"] == expected_url


def test_rerank_reuses_embedding_key_and_base_url_when_omitted(
    rerank_settings, monkeypatch
):
    monkeypatch.setattr(reranker_module.settings, "rerank_api_key", "")
    monkeypatch.setattr(reranker_module.settings, "rerank_base_url", "")

    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return FakeResponse(200, {"results": [{"index": 0, "relevance_score": 1.0}]})

    monkeypatch.setattr(reranker_module.requests, "post", fake_post)

    reranker_module.Reranker().rerank("query", ["doc"])

    assert captured["url"] == "https://api.siliconflow.cn/v1/rerank"
    assert captured["headers"]["Authorization"] == "Bearer embed-key"
