from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
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

    # LLM configuration
    llm_api_key: str
    llm_base_url: str
    llm_chat_model: str

    # Embedding configuration
    embedding_api_key: str
    embedding_base_url: str
    embedding_model: str
    embedding_document_input_type: str
    embedding_query_input_type: str
    embedding_document_prefix: str = ""
    embedding_query_prefix: str = ""
    embedding_batch_size: int = 128
    embedding_max_retries: int = 5
    embedding_retry_backoff_seconds: float = 20.0
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
    rerank_top_k: int = 15
    hybrid_alpha: float = 0.5

    @property
    def include_dirs_list(self) -> List[str]:
        """Parse comma-separated include directories."""
        return [d.strip() for d in self.docs_include_dirs.split(",")]


# Global settings instance
settings = Settings()
