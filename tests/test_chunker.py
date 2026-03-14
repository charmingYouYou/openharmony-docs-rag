#!/usr/bin/env python3
"""Regression tests for chunking edge cases."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.chunker import HeadingAwareChunker
from app.core.parser import MarkdownParser
from app.settings import settings


def test_api_reference_summary_tables_are_split_below_safe_limit():
    base_path = Path(settings.docs_local_path)
    path = base_path / "zh-cn/application-dev/reference/apis-arkui/capi-native-type-h.md"

    parser = MarkdownParser()
    chunker = HeadingAwareChunker()
    parsed = parser.parse_file(path, base_path)

    chunks = chunker.chunk_document(parsed)

    assert max(len(chunk.text) for chunk in chunks) <= settings.chunk_target_size * 8
    assert (
        sum(1 for chunk in chunks if chunk.heading_path.endswith("汇总 > 函数")) > 1
    )


def test_chunk_ids_remain_unique_after_large_api_reference_is_split():
    base_path = Path(settings.docs_local_path)
    path = base_path / "zh-cn/application-dev/reference/apis-arkui/capi-native-type-h.md"

    parser = MarkdownParser()
    chunker = HeadingAwareChunker()
    parsed = parser.parse_file(path, base_path)

    chunks = chunker.chunk_document(parsed)

    assert len(chunks) == len({chunk.chunk_id for chunk in chunks})
