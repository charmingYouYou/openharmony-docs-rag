#!/usr/bin/env python3
"""Regression tests for Qdrant client helpers."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.qdrant_client import QdrantClient
from app.schemas import RetrievalFilters


def test_count_points_uses_count_api():
    client = QdrantClient.__new__(QdrantClient)
    client.collection_name = "test-collection"
    client.client = SimpleNamespace(
        count=lambda collection_name, exact: SimpleNamespace(count=42)
    )

    assert client.count_points() == 42


def test_build_filter_excludes_readme_with_must_not():
    client = QdrantClient.__new__(QdrantClient)

    filter_obj = client._build_filter(RetrievalFilters(exclude_readme=True))

    assert filter_obj.must is None
    assert len(filter_obj.must_not) == 1
    assert filter_obj.must_not[0].key == "page_kind"
    assert filter_obj.must_not[0].match.value == "readme"
