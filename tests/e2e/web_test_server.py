"""Factory entrypoint for launching the built web console with isolated runtime settings."""

from __future__ import annotations

import os
from pathlib import Path

from app.main import create_app
from app.settings import SettingsProvider


def _required_env(name: str) -> Path:
    """Return one required path-like environment variable for the E2E server."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"缺少必需环境变量 {name}")
    return Path(value)


def create_e2e_app():
    """Create the FastAPI app bound to the temporary E2E override env and built frontend."""
    repo_root = Path(__file__).resolve().parents[2]
    override_env = _required_env("WEB_E2E_OVERRIDE_ENV")
    web_dist_dir = _required_env("WEB_E2E_WEB_DIST_DIR")
    provider = SettingsProvider(
        env_files=(
            repo_root / "deploy" / "app.env",
            repo_root / ".env",
            override_env,
        )
    )
    return create_app(web_dist_dir=web_dist_dir, settings_provider=provider)
