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
