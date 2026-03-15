#!/usr/bin/env python3
"""Pytest orchestration for browser-driven build workflow validation against isolated runtime state."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
import uuid

import pytest
import requests
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.settings import SettingsProvider
from app.storage.qdrant_client import QdrantClient


DOC_COUNT = 150


def _repo_root() -> Path:
    """Return the repository root for commands and temporary asset resolution."""
    return Path(__file__).resolve().parents[2]


def _find_free_port() -> int:
    """Reserve and return one ephemeral localhost port for the temporary API server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _run_command(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    """Run one subprocess command and raise immediately on any non-zero exit status."""
    subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=True,
        text=True,
    )


def _write_sample_document(doc_path: Path, *, relative_path: str, index: int) -> tuple[str, str]:
    """Create one deterministic Markdown document and return its repo-relative path and title."""
    title = f"E2E Guide {index:03d}"
    repeated_paragraph = (
        "This synthetic document exists to validate clone, incremental indexing, "
        "pause and resume, and full rebuild behavior through the deployed web UI.\n"
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(
        "\n".join(
            [
                f"# {title}",
                "",
                "## Overview",
                repeated_paragraph * 8,
                "## Checklist",
                "- build workflow",
                "- readonly explorer",
                "- isolated sqlite table",
                "- isolated qdrant collection",
                "",
                f"Document number: {index}",
            ]
        ),
        encoding="utf-8",
    )
    return relative_path, title


def _create_sample_repo(repo_dir: Path, doc_count: int) -> tuple[str, str]:
    """Create a local Git repository containing deterministic docs used by the sync workflow."""
    _run_command(["git", "init", "-b", "master"], cwd=repo_dir)
    _run_command(["git", "config", "user.name", "Codex E2E"], cwd=repo_dir)
    _run_command(["git", "config", "user.email", "codex-e2e@example.com"], cwd=repo_dir)

    expected_relative_path = ""
    expected_title = ""
    for index in range(1, doc_count + 1):
        top_dir = "application-dev" if index <= doc_count // 2 else "design"
        doc_path = (
            repo_dir
            / "zh-cn"
            / top_dir
            / "e2e"
            / f"doc-{index:03d}.md"
        )
        relative_path, title = _write_sample_document(
            doc_path,
            relative_path=str(doc_path.relative_to(repo_dir).as_posix()),
            index=index,
        )
        if index == 1:
            expected_relative_path = relative_path
            expected_title = title

    _run_command(["git", "add", "."], cwd=repo_dir)
    _run_command(["git", "commit", "-m", "Seed E2E sample docs"], cwd=repo_dir)
    return expected_relative_path, expected_title


def _write_override_env(
    env_path: Path,
    *,
    api_port: int,
    sqlite_db_path: Path,
    sqlite_table: str,
    qdrant_collection: str,
    docs_repo_url: Path,
    docs_local_path: Path,
) -> None:
    """Write the isolated override env used by the temporary E2E server."""
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "\n".join(
            [
                "API_HOST=127.0.0.1",
                f"API_PORT={api_port}",
                "QDRANT_HOST=127.0.0.1",
                "QDRANT_PORT=6333",
                f"SQLITE_DB_PATH={sqlite_db_path}",
                f"SQLITE_DOCUMENTS_TABLE={sqlite_table}",
                f"QDRANT_COLLECTION={qdrant_collection}",
                f"DOCS_REPO_URL={docs_repo_url}",
                "DOCS_BRANCH=master",
                f"DOCS_LOCAL_PATH={docs_local_path}",
                "DOCS_INCLUDE_DIRS=zh-cn/application-dev,zh-cn/design",
                "EMBEDDING_INTER_BATCH_DELAY_SECONDS=0.03",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _resolve_runtime_settings() -> tuple[object, Path]:
    """Load the baseline runtime config and skip when required online dependencies are unavailable."""
    repo_root = _repo_root()
    provider = SettingsProvider(
        env_files=(repo_root / "deploy" / "app.env", repo_root / ".env")
    )
    try:
        settings_snapshot = provider.get_settings()
    except ValidationError as exc:
        pytest.skip(f"deploy/app.env 未提供完整在线依赖配置：{exc}")

    parsed_embedding = urlsplit(settings_snapshot.embedding_base_url)
    if not parsed_embedding.hostname:
        pytest.skip("EMBEDDING_BASE_URL 未配置可解析主机名")

    try:
        with socket.create_connection(
            (settings_snapshot.qdrant_host, settings_snapshot.qdrant_port),
            timeout=2.0,
        ):
            pass
    except OSError:
        pytest.skip("Qdrant TCP 端口未就绪，跳过 web_build_e2e")

    try:
        QdrantClient(settings_snapshot=settings_snapshot).client.get_collections()
    except Exception as exc:
        pytest.skip(f"Qdrant API 未就绪，跳过 web_build_e2e：{exc}")

    return settings_snapshot, repo_root


def _wait_for_server(base_url: str, timeout_seconds: int = 60) -> None:
    """Poll the temporary server until both the API and built SPA entrypoint are reachable."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            capabilities = requests.get(f"{base_url}/capabilities", timeout=2.0)
            index_page = requests.get(f"{base_url}/", timeout=2.0)
            if capabilities.ok and index_page.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError(f"Timed out waiting for {base_url}")


@pytest.mark.web_build_e2e
def test_web_build_workflows_via_playwright(tmp_path: Path) -> None:
    """Run the isolated browser workflow that covers sync, pause/resume, incremental, full rebuild, and explorer detail view."""
    settings_snapshot, repo_root = _resolve_runtime_settings()

    web_dir = repo_root / "web"
    dist_dir = web_dir / "dist"
    run_id = uuid.uuid4().hex[:8]
    api_port = _find_free_port()
    sqlite_db_path = tmp_path / "storage" / "metadata-e2e.db"
    sqlite_table = f"documents_e2e_{run_id}"
    qdrant_collection = f"{settings_snapshot.qdrant_collection}_e2e_{run_id}"
    source_repo_dir = tmp_path / "source-docs"
    cloned_repo_dir = tmp_path / "cloned-docs"
    override_env_path = tmp_path / "deploy" / "app.e2e.env"
    server_log_path = tmp_path / "web-e2e-server.log"

    source_repo_dir.mkdir(parents=True, exist_ok=True)
    expected_doc_path, expected_doc_title = _create_sample_repo(source_repo_dir, DOC_COUNT)
    _write_override_env(
        override_env_path,
        api_port=api_port,
        sqlite_db_path=sqlite_db_path,
        sqlite_table=sqlite_table,
        qdrant_collection=qdrant_collection,
        docs_repo_url=source_repo_dir,
        docs_local_path=cloned_repo_dir,
    )

    _run_command(["npm", "run", "build"], cwd=web_dir)

    server_env = os.environ.copy()
    server_env.update(
        {
            "WEB_E2E_OVERRIDE_ENV": str(override_env_path),
            "WEB_E2E_WEB_DIST_DIR": str(dist_dir),
        }
    )
    base_url = f"http://127.0.0.1:{api_port}"
    with server_log_path.open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                str(repo_root / "venv" / "bin" / "uvicorn"),
                "tests.e2e.web_test_server:create_e2e_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            cwd=repo_root,
            env=server_env,
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )

        try:
            _wait_for_server(base_url)
            playwright_env = os.environ.copy()
            playwright_env.update(
                {
                    "PLAYWRIGHT_BASE_URL": base_url,
                    "WEB_E2E_EXPECTED_DOC_PATH": expected_doc_path,
                    "WEB_E2E_EXPECTED_DOC_TITLE": expected_doc_title,
                    "CI": "1",
                }
            )
            _run_command(
                [
                    "npm",
                    "run",
                    "test:e2e",
                    "--",
                    "--config",
                    "playwright.config.ts",
                    "e2e/build-workflows.spec.ts",
                ],
                cwd=web_dir,
                env=playwright_env,
            )
        finally:
            server.terminate()
            try:
                server.wait(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)

            try:
                QdrantClient(
                    settings_snapshot=settings_snapshot,
                    collection_name=qdrant_collection,
                ).clear_collection()
            except Exception:
                pass

            if sqlite_db_path.exists():
                sqlite_db_path.unlink()
            if cloned_repo_dir.exists():
                shutil.rmtree(cloned_repo_dir)
