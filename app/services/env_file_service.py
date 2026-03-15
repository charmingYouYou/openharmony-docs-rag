"""Read and write the tracked Docker deployment env file for the web console."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.schemas import EnvPayload


CORE_ENV_KEYS = [
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_CHAT_MODEL",
    "EMBEDDING_API_KEY",
    "EMBEDDING_BASE_URL",
    "EMBEDDING_MODEL",
    "DOCS_LOCAL_PATH",
]

DEFAULT_DEPLOY_ENV_PATH = Path("deploy/app.env")


class EnvFileService:
    """Manage the tracked deployment env file used by Docker and the Python API."""

    def __init__(self, env_path: str | Path = DEFAULT_DEPLOY_ENV_PATH):
        self.env_path = Path(env_path)

    def read_env(self) -> EnvPayload:
        """Return the raw env file with lightweight validation warnings."""
        raw = ""
        last_modified = None

        if self.env_path.exists():
            raw = self.env_path.read_text(encoding="utf-8")
            last_modified = datetime.fromtimestamp(
                self.env_path.stat().st_mtime
            ).isoformat(timespec="seconds")

        warnings = self._collect_warnings(raw)
        if not self.env_path.exists():
            warnings.insert(
                0,
                f"未找到部署配置文件 {self.env_path.as_posix()}，请先恢复该文件后再保存。",
            )

        return EnvPayload(raw=raw, warnings=warnings, last_modified=last_modified)

    def write_env(self, raw: str) -> EnvPayload:
        """Validate and save raw env text atomically."""
        self._validate_raw_env(raw)
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        self.env_path.write_text(raw, encoding="utf-8")
        return self.read_env()

    def _validate_raw_env(self, raw: str):
        """Reject obviously malformed env lines."""
        for line_number, line in enumerate(raw.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                raise ValueError(f"第 {line_number} 行缺少 '='：{line}")
            key, _ = stripped.split("=", 1)
            if not key.strip():
                raise ValueError(f"第 {line_number} 行环境变量名为空")

    def _collect_warnings(self, raw: str) -> list[str]:
        """Return missing-core-config warnings in Chinese."""
        values: dict[str, str] = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()

        warnings = []
        for key in CORE_ENV_KEYS:
            if not values.get(key):
                warnings.append(f"缺少 {key}")
        return warnings
