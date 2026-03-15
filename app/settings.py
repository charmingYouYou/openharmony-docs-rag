"""Runtime settings models and provider helpers for hot-reloadable env-backed config."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Iterable, List, Sequence

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_ENV_FILES = (".env", "deploy/app.env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "openharmony-docs-zh-cn"

    # SQLite Configuration
    sqlite_db_path: str = "./storage/metadata.db"
    sqlite_documents_table: str = "documents"

    # LLM configuration
    llm_api_key: str
    llm_base_url: str
    llm_chat_model: str

    # Embedding configuration
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_document_input_type: str = "document"
    embedding_query_input_type: str = "query"
    embedding_document_prefix: str = ""
    embedding_query_prefix: str = ""
    embedding_batch_size: int = 512
    embedding_max_retries: int = 5
    embedding_retry_backoff_seconds: float = 2.0
    embedding_inter_batch_delay_seconds: float = 0.0

    # Documentation Repository Configuration
    docs_repo_url: str = "https://gitee.com/openharmony/docs.git"
    docs_branch: str = "master"
    docs_local_path: str = "./data/raw/openharmony-docs"
    docs_include_dirs: str = "zh-cn/application-dev,zh-cn/design"

    # Chunking Configuration
    chunk_target_size: int = 600
    chunk_overlap: int = 100

    # Retrieval Configuration
    retrieval_top_k: int = 8
    rerank_enabled: bool = False
    rerank_api_key: str = ""
    rerank_base_url: str = ""
    rerank_model: str = ""
    rerank_top_k: int = 15
    rerank_max_retries: int = 5
    rerank_retry_backoff_seconds: float = 2.0
    hybrid_alpha: float = 0.5

    @property
    def include_dirs_list(self) -> List[str]:
        """Parse comma-separated include directories."""
        return [d.strip() for d in self.docs_include_dirs.split(",")]

    @property
    def effective_rerank_api_key(self) -> str:
        """Reuse embedding API key when rerank key is not set."""
        return self.rerank_api_key or self.embedding_api_key

    @property
    def effective_rerank_base_url(self) -> str:
        """Reuse embedding base URL when rerank base URL is not set."""
        return self.rerank_base_url or self.embedding_base_url

    @property
    def rerank_is_configured(self) -> bool:
        """Return whether rerank has enough config to be enabled."""
        return bool(
            self.rerank_enabled
            and self.rerank_model
            and self.effective_rerank_api_key
            and self.effective_rerank_base_url
        )


class SettingsProvider:
    """Load and cache settings snapshots from one or more env files."""

    def __init__(self, env_files: Sequence[str | Path] = DEFAULT_ENV_FILES):
        self.env_files = tuple(Path(path) for path in env_files)
        self._lock = RLock()
        self._cached_settings: Settings | None = None
        self._cached_signature: tuple[tuple[str, int | None], ...] | None = None
        self._generation = 0

    def get_settings(self) -> Settings:
        """Return the latest settings snapshot, reloading when source files change."""
        with self._lock:
            current_signature = self._signature()
            if (
                self._cached_settings is None
                or self._cached_signature != current_signature
            ):
                self._cached_settings = Settings(
                    _env_file=tuple(path.as_posix() for path in self.env_files)
                )
                self._cached_signature = current_signature
            return self._cached_settings

    def invalidate(self) -> None:
        """Force the next read to rebuild the cached settings snapshot."""
        with self._lock:
            self._cached_settings = None
            self._cached_signature = None
            self._generation += 1

    def primary_env_path(self) -> Path:
        """Return the last configured env file, treating it as the writable runtime target."""
        return self.env_files[-1]

    def _signature(self) -> tuple[tuple[str, int | None], ...]:
        """Build one comparable signature for the tracked env files."""
        return tuple(
            (path.as_posix(), self._stat_mtime_ns(path)) for path in self.env_files
        )

    def _stat_mtime_ns(self, path: Path) -> int | None:
        """Return one file mtime for cache invalidation, handling missing files."""
        if not path.exists():
            return None
        return path.stat().st_mtime_ns


class SettingsProxy:
    """Backward-compatible proxy that resolves attributes from the latest provider snapshot."""

    def __getattr__(self, name: str):
        """Read attributes from the current settings snapshot."""
        return getattr(get_settings(), name)


_settings_provider = SettingsProvider()


def get_settings_provider() -> SettingsProvider:
    """Return the process-wide settings provider."""
    return _settings_provider


def set_settings_provider(provider: SettingsProvider) -> SettingsProvider:
    """Swap the process-wide settings provider for tests or custom app wiring."""
    global _settings_provider
    _settings_provider = provider
    return _settings_provider


def get_settings() -> Settings:
    """Return the latest settings snapshot from the active provider."""
    return get_settings_provider().get_settings()


# Backward-compatible attribute access for modules that still import `settings`.
settings = SettingsProxy()
