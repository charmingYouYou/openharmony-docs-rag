"""Runtime service discovery for the local web console."""

from __future__ import annotations

from pathlib import Path
import socket

from app.schemas import ServiceStatus
from app.settings import settings


class ServiceStatusService:
    """Collect health-like status for local runtime dependencies."""

    def list_services(self) -> list[ServiceStatus]:
        """Return the currently configured service endpoints."""
        db_path = Path(settings.sqlite_db_path)
        qdrant_ok = self._tcp_check(settings.qdrant_host, settings.qdrant_port)

        return [
            ServiceStatus(
                name="API",
                status="healthy",
                host=settings.api_host,
                port=settings.api_port,
                details="Web API 已加载，可通过当前进程访问。",
            ),
            ServiceStatus(
                name="Qdrant",
                status="healthy" if qdrant_ok else "degraded",
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                details="连接正常" if qdrant_ok else "无法建立 TCP 连接",
            ),
            ServiceStatus(
                name="SQLite",
                status="healthy" if db_path.exists() else "degraded",
                host="local",
                port=0,
                details=(
                    f"数据库文件：{db_path}"
                    if db_path.exists()
                    else f"数据库文件不存在：{db_path}"
                ),
            ),
        ]

    def _tcp_check(self, host: str, port: int) -> bool:
        """Check whether one TCP endpoint is reachable."""
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False
