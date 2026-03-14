#!/usr/bin/env python3
"""Regression tests for query preprocessing behavior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas import QueryIntent
from app.utils.query_preprocessor import QueryPreprocessor


def test_guide_queries_do_not_force_page_kind_filter():
    result = QueryPreprocessor().preprocess("如何创建 UIAbility 组件？")

    assert result.intent == QueryIntent.GUIDE
    assert result.filters.exclude_readme is True
    assert result.filters.page_kind is None


def test_api_like_queries_prefer_api_usage_intent():
    preprocessor = QueryPreprocessor()

    assert preprocessor.preprocess("router.pushUrl 方法如何使用？").intent == QueryIntent.API_USAGE
    assert preprocessor.preprocess("@State 装饰器如何使用？").intent == QueryIntent.API_USAGE
    assert preprocessor.preprocess("Text 组件有哪些属性？").intent == QueryIntent.API_USAGE


def test_explicitly_out_of_scope_queries_fall_back_to_general():
    preprocessor = QueryPreprocessor()

    assert preprocessor.preprocess("如何在 Android 上开发应用？").intent == QueryIntent.GENERAL
    assert preprocessor.preprocess("Python 如何读取文件？").intent == QueryIntent.GENERAL
