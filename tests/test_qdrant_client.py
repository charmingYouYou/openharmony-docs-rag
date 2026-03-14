#!/usr/bin/env python3
"""Regression tests for Qdrant client helpers."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.qdrant_client import QdrantClient


def test_count_points_uses_count_api():
    client = QdrantClient.__new__(QdrantClient)
    client.collection_name = "test-collection"
    client.client = SimpleNamespace(
        count=lambda collection_name, exact: SimpleNamespace(count=42)
    )

    assert client.count_points() == 42
