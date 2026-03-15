#!/usr/bin/env python3
"""Tests for the local web console management APIs."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.services.env_file_service import EnvFileService
from app.settings import SettingsProvider


class FakeBuildManager:
    """Small stand-in for the in-memory build manager."""

    def __init__(self):
        self.started_modes = []
        self.paused = []
        self.resumed = []
        self.runs = {
            "run-1": {
                "id": "run-1",
                "mode": "sync_incremental",
                "status": "paused",
                "stage": "indexing",
                "started_at": "2026-03-14T10:00:00",
                "updated_at": "2026-03-14T10:05:00",
                "processed_docs": 12,
                "total_docs": 100,
                "indexed_docs": 10,
                "reindexed_docs": 2,
                "skipped_docs": 0,
                "failed_docs": 0,
                "current_path": "zh-cn/application-dev/demo.md",
                "can_pause": False,
                "can_resume": True,
            }
        }

    def list_runs(self):
        return list(self.runs.values())

    def get_run(self, run_id):
        return self.runs.get(run_id)

    def start_run(self, mode):
        self.started_modes.append(mode)
        run = {
            **self.runs["run-1"],
            "id": "run-2",
            "mode": mode,
            "status": "running",
            "can_pause": True,
            "can_resume": False,
        }
        self.runs["run-2"] = run
        return run

    def request_pause(self, run_id):
        self.paused.append(run_id)
        return {
            **self.runs[run_id],
            "status": "pausing",
            "can_pause": False,
            "can_resume": False,
        }

    def resume_run(self, run_id):
        self.resumed.append(run_id)
        return {
            **self.runs[run_id],
            "mode": "incremental",
            "status": "running",
            "can_pause": True,
            "can_resume": False,
        }

    async def stream_events(self, run_id):
        yield {
            "event": "progress",
            "data": {
                "message": "开始同步文档仓库",
                "stage": "syncing_repo",
            },
        }
        yield {
            "event": "completed",
            "data": {
                "message": "构建任务已完成",
                "stage": "completed",
            },
        }


class FakeEnvService:
    """Fake env file service."""

    def __init__(self):
        self.saved = []
        self.env_path = Path("deploy/app.env")

    def read_env(self):
        return {
            "raw": "LLM_API_KEY=sk-demo\nAPI_PORT=8000\n",
            "warnings": ["缺少 EMBEDDING_API_KEY"],
            "last_modified": "2026-03-14T10:00:00",
        }

    def write_env(self, raw):
        self.saved.append(raw)
        return {
            "raw": raw,
            "warnings": [],
            "last_modified": "2026-03-14T10:05:00",
        }


class FakeServiceStatusService:
    """Fake service discovery layer."""

    def list_services(self):
        return [
            {
                "name": "API",
                "status": "healthy",
                "host": "0.0.0.0",
                "port": 8000,
                "details": "服务运行中",
            },
            {
                "name": "Qdrant",
                "status": "degraded",
                "host": "localhost",
                "port": 6333,
                "details": "连接失败",
            },
        ]


def write_runtime_env(env_path: Path, sqlite_db_path: Path) -> None:
    """Write one minimal env file that satisfies app startup validation."""
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
                "LLM_CHAT_MODEL=qwen-max",
                "EMBEDDING_API_KEY=sk-embed",
                "EMBEDDING_BASE_URL=https://embed.example.com/v1",
                "EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B",
                f"SQLITE_DB_PATH={sqlite_db_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Create one test client with fake web services and a scoped runtime settings provider."""
    from app.api.web import builds, config, services

    monkeypatch.setattr(builds, "build_manager", FakeBuildManager())
    monkeypatch.setattr(config, "env_service", FakeEnvService())
    monkeypatch.setattr(services, "service_status_service", FakeServiceStatusService())
    env_path = tmp_path / "deploy" / "app.env"
    sqlite_db_path = tmp_path / "storage" / "metadata.db"
    write_runtime_env(env_path, sqlite_db_path)
    provider = SettingsProvider(env_files=(env_path,))
    return TestClient(create_app(settings_provider=provider))


def test_build_routes_expose_start_pause_resume_and_list(client):
    response = client.post("/web/builds", json={"mode": "sync_incremental"})

    assert response.status_code == 200
    assert response.json()["mode"] == "sync_incremental"
    assert response.json()["status"] == "running"

    response = client.get("/web/builds")

    assert response.status_code == 200
    assert len(response.json()) >= 1

    response = client.post("/web/builds/run-1/pause")

    assert response.status_code == 200
    assert response.json()["status"] == "pausing"

    response = client.post("/web/builds/run-1/resume")

    assert response.status_code == 200
    assert response.json()["mode"] == "incremental"
    assert response.json()["status"] == "running"


def test_build_events_stream_uses_sse(client):
    with client.stream("GET", "/web/builds/run-1/events") as response:
        payload = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: progress" in payload
    assert "开始同步文档仓库" in payload
    assert "event: completed" in payload


def test_env_routes_read_and_write_raw_env_text(client):
    response = client.get("/web/env")

    assert response.status_code == 200
    assert "LLM_API_KEY=sk-demo" in response.json()["raw"]
    assert response.json()["warnings"] == ["缺少 EMBEDDING_API_KEY"]

    response = client.put("/web/env", json={"raw": "API_PORT=9000\n"})

    assert response.status_code == 200
    assert response.json()["raw"] == "API_PORT=9000\n"
    assert response.json()["warnings"] == []


def test_env_routes_use_deploy_app_env_service_target(client):
    from app.api.web import config

    assert config.env_service.env_path == Path("deploy/app.env")


def test_env_file_service_returns_actionable_warning_when_deploy_env_is_missing(tmp_path):
    service = EnvFileService(tmp_path / "deploy" / "app.env")

    payload = service.read_env()

    assert payload.raw == ""
    assert any("deploy/app.env" in warning for warning in payload.warnings)


def test_services_route_lists_runtime_status(client):
    response = client.get("/web/services")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "API"
    assert response.json()[0]["port"] == 8000
    assert response.json()[1]["status"] == "degraded"
