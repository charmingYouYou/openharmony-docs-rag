#!/usr/bin/env python3
"""Regression tests for runtime settings reload and scoped document browsing."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.settings import SettingsProvider
from app.storage.models import DocumentModel
from app.storage.sqlite_client import SQLiteClient


def write_env_file(
    env_path: Path,
    *,
    llm_chat_model: str,
    embedding_model: str,
    sqlite_db_path: Path,
    sqlite_documents_table: str = "documents",
) -> None:
    """Write one minimal runtime env file for provider-backed tests."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "\n".join(
            [
                "API_HOST=127.0.0.1",
                "API_PORT=8000",
                "QDRANT_HOST=127.0.0.1",
                "QDRANT_PORT=6333",
                "LLM_API_KEY=sk-chat",
                "LLM_BASE_URL=https://llm.example.com/v1",
                f"LLM_CHAT_MODEL={llm_chat_model}",
                "EMBEDDING_API_KEY=sk-embed",
                "EMBEDDING_BASE_URL=https://embed.example.com/v1",
                f"EMBEDDING_MODEL={embedding_model}",
                f"SQLITE_DB_PATH={sqlite_db_path}",
                f"SQLITE_DOCUMENTS_TABLE={sqlite_documents_table}",
                "DOCS_LOCAL_PATH=./data/raw/openharmony-docs",
                "DOCS_INCLUDE_DIRS=zh-cn/application-dev,zh-cn/design",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_capabilities_follow_provider_reload(tmp_path: Path) -> None:
    """New requests should observe refreshed env-backed capabilities after provider invalidation."""
    env_path = tmp_path / "deploy" / "app.env"
    db_path = tmp_path / "storage" / "metadata.db"
    write_env_file(
        env_path,
        llm_chat_model="kimi-k2.5",
        embedding_model="Qwen/Qwen3-Embedding-4B",
        sqlite_db_path=db_path,
    )
    provider = SettingsProvider(env_files=(env_path,))

    with TestClient(create_app(settings_provider=provider)) as client:
        first = client.get("/capabilities")
        assert first.status_code == 200
        assert first.json()["chat_model"] == "kimi-k2.5"
        assert first.json()["embedding_model"] == "Qwen/Qwen3-Embedding-4B"

        write_env_file(
            env_path,
            llm_chat_model="qwen-plus",
            embedding_model="Qwen/Qwen3-Embedding-8B",
            sqlite_db_path=db_path,
        )
        provider.invalidate()

        second = client.get("/capabilities")
        assert second.status_code == 200
        assert second.json()["chat_model"] == "qwen-plus"
        assert second.json()["embedding_model"] == "Qwen/Qwen3-Embedding-8B"


def test_web_env_route_writes_provider_primary_env_file(tmp_path: Path) -> None:
    """The web env editor should target the active provider primary file rather than the default deploy path."""
    base_env_path = tmp_path / "deploy" / "app.env"
    override_env_path = tmp_path / "runtime" / "override.env"
    db_path = tmp_path / "storage" / "metadata.db"
    write_env_file(
        base_env_path,
        llm_chat_model="kimi-k2.5",
        embedding_model="Qwen/Qwen3-Embedding-4B",
        sqlite_db_path=db_path,
    )
    override_env_path.parent.mkdir(parents=True, exist_ok=True)
    override_env_path.write_text(
        "LLM_CHAT_MODEL=qwen-plus\nEMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B\n",
        encoding="utf-8",
    )
    provider = SettingsProvider(env_files=(base_env_path, override_env_path))

    with TestClient(create_app(settings_provider=provider)) as client:
        updated = client.put(
            "/web/env",
            json={
                "raw": "\n".join(
                    [
                        "LLM_API_KEY=sk-chat",
                        "LLM_BASE_URL=https://llm.example.com/v1",
                        "LLM_CHAT_MODEL=glm-4.5",
                        "EMBEDDING_API_KEY=sk-embed",
                        "EMBEDDING_BASE_URL=https://embed.example.com/v1",
                        "EMBEDDING_MODEL=BAAI/bge-m3",
                        f"SQLITE_DB_PATH={db_path}",
                        "DOCS_LOCAL_PATH=./data/raw/openharmony-docs",
                    ]
                )
                + "\n"
            },
        )
        assert updated.status_code == 200
        assert "LLM_CHAT_MODEL=glm-4.5" not in base_env_path.read_text(encoding="utf-8")
        assert "LLM_CHAT_MODEL=glm-4.5" in override_env_path.read_text(encoding="utf-8")
        assert client.get("/capabilities").json()["chat_model"] == "glm-4.5"


@pytest.mark.asyncio
async def test_document_endpoints_use_scoped_sqlite_table_and_expose_read_only_detail(
    tmp_path: Path,
) -> None:
    """Document browsing should read from the configured table and expose one detail endpoint."""
    env_path = tmp_path / "deploy" / "app.env"
    db_path = tmp_path / "storage" / "metadata.db"
    table_name = "documents_e2e_scope"
    write_env_file(
        env_path,
        llm_chat_model="kimi-k2.5",
        embedding_model="Qwen/Qwen3-Embedding-4B",
        sqlite_db_path=db_path,
        sqlite_documents_table=table_name,
    )

    sqlite = SQLiteClient(db_path=str(db_path), table_name=table_name)
    await sqlite.initialize()
    await sqlite.insert_document(
        DocumentModel(
            doc_id="doc-1",
            path="zh-cn/application-dev/doc-1.md",
            title="Doc 1",
            source_url="https://example.com/doc-1",
            top_dir="application-dev",
            sub_dir="guide",
            page_kind="guide",
            kit="ArkUI",
            index_status="ready",
            chunk_count=3,
            indexed_chunk_count=3,
        )
    )

    provider = SettingsProvider(env_files=(env_path,))
    with TestClient(create_app(settings_provider=provider)) as client:
        listing = client.get("/documents")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1
        assert listing.json()["documents"][0]["doc_id"] == "doc-1"

        detail = client.get("/documents/doc-1")
        assert detail.status_code == 200
        assert detail.json()["doc_id"] == "doc-1"
        assert detail.json()["title"] == "Doc 1"
        assert detail.json()["source_url"] == "https://example.com/doc-1"
        assert detail.json()["chunk_count"] == 3
        assert detail.json()["indexed_chunk_count"] == 3
