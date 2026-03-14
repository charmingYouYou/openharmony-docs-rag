#!/usr/bin/env python3
"""Regression tests for answer relevance checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import RetrievedChunk
from app.services.answer_service import AnswerService


def make_chunk(text: str, score: float = 0.8, path: str = "doc.md", heading: str = "Heading"):
    return RetrievedChunk(
        chunk_id="chunk-1",
        text=text,
        heading_path=heading,
        score=score,
        metadata={"path": path},
    )


def test_check_relevance_rejects_missing_anchor_terms():
    service = AnswerService()
    chunks = [
        make_chunk("这些文档介绍 OpenHarmony 文件管理 API，例如 fs.read 和 AtomicFile。"),
    ]

    assert service.check_relevance("Python 如何读取文件？", chunks) is False


def test_check_relevance_keeps_matching_anchor_terms():
    service = AnswerService()
    chunks = [
        make_chunk("UIAbility 的 onCreate 方法接收 want 和 launchParam 两个参数。"),
    ]

    assert service.check_relevance("UIAbility 的 onCreate 方法有哪些参数？", chunks) is True
