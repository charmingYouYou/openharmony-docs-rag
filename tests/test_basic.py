#!/usr/bin/env python3
"""Simple test script to verify basic functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        from app.settings import settings
        print("✓ Settings loaded")

        from app.schemas import ParsedDocument, Chunk, QueryIntent
        print("✓ Schemas imported")

        from app.core.parser import MarkdownParser
        print("✓ Parser imported")

        from app.core.chunker import HeadingAwareChunker
        print("✓ Chunker imported")

        from app.core.embedder import Embedder
        print("✓ Embedder imported")

        from app.storage.qdrant_client import QdrantClient
        print("✓ Qdrant client imported")

        from app.storage.sqlite_client import SQLiteClient
        print("✓ SQLite client imported")

        from app.utils.query_preprocessor import QueryPreprocessor
        print("✓ Query preprocessor imported")

        from app.services.retriever import HybridRetriever
        print("✓ Retriever imported")

        print("\n✅ All imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        return False


def test_parser():
    """Test parser with sample markdown."""
    print("\nTesting parser...")

    try:
        from app.core.parser import MarkdownParser

        parser = MarkdownParser()

        # Test metadata extraction
        sample_content = """
<!--
Kit: ArkUI
Subsystem: arkui_ace_engine
Owner: @someone
-->

# Sample Document

This is a test document.

## Section 1

Content here.
"""

        metadata = parser.extract_metadata(sample_content)
        assert metadata.kit == "ArkUI"
        assert metadata.subsystem == "arkui_ace_engine"
        print("✓ Metadata extraction works")

        # Test title extraction
        title = parser.extract_title(sample_content)
        assert title == "Sample Document"
        print("✓ Title extraction works")

        print("\n✅ Parser tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Parser test failed: {e}")
        return False


def test_query_preprocessor():
    """Test query preprocessor."""
    print("\nTesting query preprocessor...")

    try:
        from app.utils.query_preprocessor import QueryPreprocessor
        from app.schemas import QueryIntent

        preprocessor = QueryPreprocessor()

        # Test guide intent
        result = preprocessor.preprocess("如何创建 UIAbility 组件？")
        assert result.intent == QueryIntent.GUIDE
        print(f"✓ Guide intent detected: {result.intent} (confidence: {result.confidence:.2f})")

        # Test API intent
        result = preprocessor.preprocess("UIAbility 的 onCreate 方法参数是什么？")
        assert result.intent == QueryIntent.API_USAGE
        print(f"✓ API intent detected: {result.intent} (confidence: {result.confidence:.2f})")

        # Test design spec intent
        result = preprocessor.preprocess("ArkUI 组件的设计规范是什么？")
        assert result.intent == QueryIntent.DESIGN_SPEC
        print(f"✓ Design spec intent detected: {result.intent} (confidence: {result.confidence:.2f})")

        print("\n✅ Query preprocessor tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Query preprocessor test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("OpenHarmony Docs RAG - Basic Functionality Tests")
    print("=" * 60)

    results = []

    results.append(("Imports", test_imports()))
    results.append(("Parser", test_parser()))
    results.append(("Query Preprocessor", test_query_preprocessor()))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
