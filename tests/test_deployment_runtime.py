#!/usr/bin/env python3
"""Tests for deployment-time runtime behaviors such as static web serving."""

from pathlib import Path
import sys

from fastapi.testclient import TestClient
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import create_app


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


def test_delivery_compose_pulls_prebuilt_image():
    """The delivery compose stack should install from a registry image instead of local source builds."""
    repo_root = Path(__file__).parent.parent
    compose_path = repo_root / "docker-compose.yml"

    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    app_service = payload["services"]["app"]

    assert "image" in app_service
    assert "build" not in app_service


def test_install_script_uses_pull_and_not_local_build():
    """The direct-install script should pull published images instead of rebuilding from source."""
    repo_root = Path(__file__).parent.parent
    script_path = repo_root / "deploy" / "deploy.sh"

    script = script_path.read_text(encoding="utf-8")

    assert "compose pull" in script
    assert "up -d --build" not in script


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
