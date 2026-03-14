#!/usr/bin/env python3
"""Regression tests for evaluation metrics."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.eval import RAGEvaluator


def test_out_of_scope_refusals_count_as_success():
    evaluator = RAGEvaluator.__new__(RAGEvaluator)

    metrics = evaluator._calculate_metrics(
        preprocessed=SimpleNamespace(intent=SimpleNamespace(value="general"), confidence=0.9),
        chunks=[],
        answer="未找到相关信息",
        citations=[],
        expected_intent="general",
        expected_docs=[],
        expected_keywords=["未找到", "相关信息"],
        question_type="out_of_scope",
    )

    assert metrics["doc_recall"] == 1.0
    assert metrics["has_answer"] is False
    assert metrics["overall_success"] is True
