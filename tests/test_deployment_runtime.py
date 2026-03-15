#!/usr/bin/env python3
"""Tests for deployment-time runtime behaviors such as static web serving."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app
from app.settings import Settings


def test_settings_read_deploy_app_env_and_ignore_compose_only_keys(tmp_path):
    """Deployment settings should accept compose-only keys while reading the tracked app env file."""
    env_path = tmp_path / "deploy" / "app.env"
    env_path.parent.mkdir(parents=True)
    env_path.write_text(
        "\n".join(
            [
                "LLM_API_KEY=sk-chat",
                "LLM_BASE_URL=https://llm.example.com/v1",
                "LLM_CHAT_MODEL=qwen-max",
                "EMBEDDING_API_KEY=sk-embed",
                "EMBEDDING_BASE_URL=https://embed.example.com/v1",
                "EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B",
                "OPENHARMONY_RAG_IMAGE=ghcr.io/example/app:latest",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_path)

    assert settings.llm_chat_model == "qwen-max"
    assert settings.embedding_model == "Qwen/Qwen3-Embedding-4B"


def test_serves_built_web_assets_and_spa_routes(tmp_path):
    """Deployment app should serve the built web app from one shared entrypoint."""
    dist_dir = tmp_path / "web-dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>OpenHarmony 控制台</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")

    client = TestClient(create_app(web_dist_dir=dist_dir))

    root_response = client.get("/")
    route_response = client.get("/services")
    asset_response = client.get("/assets/app.js")

    assert root_response.status_code == 200
    assert "OpenHarmony 控制台" in root_response.text
    assert route_response.status_code == 200
    assert "OpenHarmony 控制台" in route_response.text
    assert asset_response.status_code == 200
    assert "console.log('ok')" in asset_response.text


def test_startup_initializes_sqlite_metadata_file(tmp_path, monkeypatch):
    """Fresh installs should create the SQLite metadata database during app startup."""
    db_path = tmp_path / "storage" / "metadata.db"

    monkeypatch.setattr("app.main.settings.sqlite_db_path", str(db_path))

    with TestClient(create_app()) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert db_path.exists()


def test_delivery_compose_pulls_prebuilt_image():
    """The delivery compose stack should install from a registry image instead of local source builds."""
    repo_root = Path(__file__).parent.parent
    compose_path = repo_root / "docker-compose.yml"

    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    app_service = payload["services"]["app"]

    assert "image" in app_service
    assert "build" not in app_service
    assert app_service["env_file"] == ["./deploy/app.env"]
    assert "./deploy/app.env:/app/deploy/app.env" in app_service["volumes"]


def test_install_script_uses_pull_and_not_local_build():
    """The direct-install script should pull published images instead of rebuilding from source."""
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "deploy" / "deploy.sh"

    script = script_path.read_text(encoding="utf-8")

    assert " pull" in script
    assert "up -d --build" not in script
    assert "--env-file" in script
    assert "deploy/app.env" in script


def test_release_workflow_runs_on_main_push_and_can_write_releases():
    """The repository should publish tags and GitHub releases from a dedicated release workflow."""
    repo_root = Path(__file__).parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "release.yml"

    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert payload["name"] == "release"
    assert payload["on"]["push"]["branches"] == ["main"]
    assert payload["jobs"]["release"]["permissions"]["contents"] == "write"


def test_semantic_release_config_generates_v_tags_and_changelog():
    """Semantic release should manage version tags, changelog updates, and GitHub releases."""
    repo_root = Path(__file__).parent.parent
    config_path = repo_root / ".releaserc.json"

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    plugins = payload["plugins"]

    assert payload["tagFormat"] == "v${version}"
    assert any(
        plugin[0] == "@semantic-release/changelog"
        and plugin[1]["changelogFile"] == "CHANGELOG.md"
        for plugin in plugins
    )
    assert any(plugin == "@semantic-release/github" for plugin in plugins)


def test_publish_image_workflow_builds_frontend_before_container_push():
    """The image workflow should validate the frontend build directly before invoking docker buildx."""
    repo_root = Path(__file__).parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "publish-image.yml"

    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = payload["jobs"]["publish"]["steps"]
    step_names = [step["name"] for step in steps]

    assert "Set up Node.js" in step_names
    assert "Install frontend dependencies" in step_names
    assert "Build frontend bundle" in step_names


def test_publish_image_workflow_builds_multi_arch_images():
    """Published install images should include both amd64 and arm64 manifests."""
    repo_root = Path(__file__).parent.parent
    workflow_path = repo_root / ".github" / "workflows" / "publish-image.yml"

    payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    steps = payload["jobs"]["publish"]["steps"]
    qemu_step = next(step for step in steps if step["name"] == "Set up QEMU")
    build_step = next(step for step in steps if step["name"] == "Build and push image")

    assert qemu_step["uses"] == "docker/setup-qemu-action@v3"
    assert build_step["with"]["platforms"] == "linux/amd64,linux/arm64"
